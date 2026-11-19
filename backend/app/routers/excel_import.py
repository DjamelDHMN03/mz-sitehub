"""
Routeur Import Excel (sections 59-60).

Flux en deux temps, comme demandé par le cahier des charges ("Afficher les
différences avant validation") :
1. POST /import/excel/preview -> parse le fichier, compare aux sites
   existants, renvoie le diff SANS RIEN ÉCRIRE en base.
2. POST /import/excel/confirm -> applique réellement les créations/mises à
   jour, seulement après validation explicite de l'utilisateur.

Limite assumée : le résultat du preview est gardé en mémoire (process
Python) entre les deux appels, avec une expiration de 30 minutes. Ça
suffit pour un déploiement V1 mono-instance (0 DA) ; une vraie file
d'attente/cache partagé (Redis) serait nécessaire pour du multi-instance —
non justifié à ce stade.
"""
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import require_permission
from app.core.upload_limits import assert_upload_size_ok
from app.db.session import get_db
from app.models.site import Site, SiteStatus, Wilaya
from app.models.user import User
from app.schemas.excel_import import ExcelConfirmRequest, ExcelPreviewResult, SyncPreviewItemOut
from app.services.excel_import import ExcelImportError, ExcelRow, build_sync_preview, parse_excel_rows

router = APIRouter(prefix="/import/excel", tags=["import-excel"])

_PREVIEW_CACHE: dict[str, tuple[float, list[ExcelRow]]] = {}
_CACHE_TTL_SECONDS = 30 * 60


def _cache_preview(rows: list[ExcelRow]) -> str:
    import_id = str(uuid.uuid4())
    _PREVIEW_CACHE[import_id] = (time.time(), rows)
    # purge best-effort des entrées expirées (pas besoin de tâche planifiée
    # séparée pour un volume V1)
    expired = [k for k, (ts, _) in _PREVIEW_CACHE.items() if time.time() - ts > _CACHE_TTL_SECONDS]
    for k in expired:
        del _PREVIEW_CACHE[k]
    return import_id


def _get_cached_rows(import_id: str) -> list[ExcelRow]:
    entry = _PREVIEW_CACHE.get(import_id)
    if entry is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Prévisualisation introuvable ou expirée (30 min) — relancez l'import",
        )
    return entry[1]


async def _load_existing_sites(db: AsyncSession, codes: list[str]) -> dict[str, dict]:
    result = await db.execute(
        select(Site, SiteStatus.label, Wilaya.name)
        .join(SiteStatus, Site.status_id == SiteStatus.id)
        .outerjoin(Wilaya, Site.wilaya_id == Wilaya.id)
        .where(Site.code.in_(codes), Site.deleted_at.is_(None))
    )
    existing: dict[str, dict] = {}
    for site, status_label, wilaya_name in result.all():
        existing[site.code] = {
            "name": site.name,
            "wilaya": wilaya_name,
            "owner_name": site.owner_name,
            "organisme": site.organisme,
            "status": status_label,
            "address": site.address,
            "observation": site.observation,
        }
    return existing


@router.post("/preview", response_model=ExcelPreviewResult)
async def preview_excel_import(
    file: UploadFile,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ExcelPreviewResult:
    content = await file.read()
    try:
        assert_upload_size_ok(content)
    except ValueError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc

    try:
        mapping, rows = parse_excel_rows(content)
    except ExcelImportError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    codes = [str(r.values["code"]).strip().upper() for r in rows if r.values.get("code")]
    existing_sites = await _load_existing_sites(db, codes)

    preview_items = build_sync_preview(rows, existing_sites)

    items_out = []
    summary = {"CREATE": 0, "UPDATE": 0, "INCHANGE": 0, "IGNORE_NO_CODE": 0}
    for item in preview_items:
        summary[item.action] += 1
        items_out.append(
            SyncPreviewItemOut(
                row_number=item.row_number,
                code=item.code,
                action=item.action,
                changes={k: list(v) for k, v in item.changes.items()},
            )
        )

    import_id = _cache_preview(rows)

    return ExcelPreviewResult(
        import_id=import_id,
        detected_columns=mapping.detected,
        unmatched_headers=mapping.unmatched_headers,
        items=items_out,
        summary=summary,
    )


@router.post("/confirm")
async def confirm_excel_import(
    payload: ExcelConfirmRequest,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = _get_cached_rows(payload.import_id)
    codes = [str(r.values["code"]).strip().upper() for r in rows if r.values.get("code")]

    # Recharge l'état actuel (peut avoir changé depuis le preview) + référentiels
    result = await db.execute(select(Site).where(Site.code.in_(codes), Site.deleted_at.is_(None)))
    sites_by_code = {s.code: s for s in result.scalars().all()}

    status_result = await db.execute(select(SiteStatus))
    status_by_label = {s.label.strip().lower(): s.id for s in status_result.scalars().all()}

    wilaya_result = await db.execute(select(Wilaya))
    wilaya_by_name = {w.name.strip().lower(): w.id for w in wilaya_result.scalars().all()}

    created, updated, skipped_unresolved = 0, 0, []
    now = datetime.now(timezone.utc)

    for row in rows:
        code = row.values.get("code")
        if not code:
            continue
        code = str(code).strip().upper()
        existing = sites_by_code.get(code)

        status_id = None
        status_value = row.values.get("status")
        if status_value:
            status_id = status_by_label.get(str(status_value).strip().lower())
            if status_id is None:
                skipped_unresolved.append(f"Ligne {row.row_number} : statut '{status_value}' non reconnu")

        wilaya_id = None
        wilaya_value = row.values.get("wilaya")
        if wilaya_value:
            wilaya_id = wilaya_by_name.get(str(wilaya_value).strip().lower())
            if wilaya_id is None:
                skipped_unresolved.append(f"Ligne {row.row_number} : wilaya '{wilaya_value}' non reconnue")

        if existing is None:
            if not payload.apply_creates:
                continue
            if status_id is None:
                # Jamais de statut inventé — sans statut résolu, impossible de créer (contrainte NOT NULL)
                skipped_unresolved.append(
                    f"Ligne {row.row_number} : site {code} non créé (statut requis non reconnu)"
                )
                continue
            new_site = Site(
                code=code,
                name=row.values.get("name"),
                wilaya_id=wilaya_id,
                address=row.values.get("address"),
                owner_name=row.values.get("owner_name"),
                organisme=row.values.get("organisme"),
                observation=row.values.get("observation"),
                status_id=status_id,
                priority=2,
                created_by=current_user.id,
                updated_by=current_user.id,
                created_at=now,
                updated_at=now,
            )
            db.add(new_site)
            created += 1
            await log_audit(
                db, user_id=current_user.id, entity="sites", entity_id=None,
                action="IMPORT_EXCEL_CREATE", new_value=code,
            )
        else:
            if not payload.apply_updates:
                continue
            changed = False
            for field_name, value in [
                ("name", row.values.get("name")), ("address", row.values.get("address")),
                ("owner_name", row.values.get("owner_name")), ("organisme", row.values.get("organisme")),
                ("observation", row.values.get("observation")),
            ]:
                if value and getattr(existing, field_name) != value:
                    setattr(existing, field_name, value)
                    changed = True
            if status_id and existing.status_id != status_id:
                existing.status_id = status_id
                changed = True
            if wilaya_id and existing.wilaya_id != wilaya_id:
                existing.wilaya_id = wilaya_id
                changed = True

            if changed:
                existing.updated_by = current_user.id
                existing.updated_at = now
                updated += 1
                await log_audit(
                    db, user_id=current_user.id, entity="sites", entity_id=existing.id,
                    action="IMPORT_EXCEL_UPDATE", new_value=code,
                )

    await db.commit()
    return {"created": created, "updated": updated, "warnings": skipped_unresolved}
