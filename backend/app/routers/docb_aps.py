"""
Routeur Doc B / APS (sections 37-38). Chaque enregistrement pointe vers un
Document déjà uploadé (Phase 11) via `document_id` — pas de duplication de
la gestion de fichier, on réutilise la GED existante.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.site import Site
from app.models.tracking import ApsDocument, DocB
from app.models.user import User
from app.schemas.docb_aps import (
    VALID_APS_TYPES,
    ApsCreate,
    ApsOut,
    ApsUpdate,
    DocBCreate,
    DocBOut,
    DocBUpdate,
)

router = APIRouter(tags=["docb-aps"])


async def _get_site_or_404(db: AsyncSession, site_id: uuid.UUID) -> Site:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.deleted_at.is_(None)))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")
    return site


# ------------------------------------------------------------------
# Doc B
# ------------------------------------------------------------------
@router.post("/sites/{site_id}/doc-b", response_model=DocBOut, status_code=status.HTTP_201_CREATED)
async def create_doc_b(
    site_id: uuid.UUID,
    payload: DocBCreate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> DocBOut:
    await _get_site_or_404(db, site_id)
    doc_b = DocB(site_id=site_id, version=payload.version or 1, **payload.model_dump(exclude={"version"}))
    db.add(doc_b)
    await db.flush()
    await log_audit(
        db, user_id=current_user.id, entity="doc_b", entity_id=doc_b.id,
        action="CREATE", new_value=doc_b.reference,
    )
    await db.commit()
    await db.refresh(doc_b)
    return DocBOut.model_validate(doc_b)


@router.get("/sites/{site_id}/doc-b", response_model=list[DocBOut])
async def list_doc_b(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocBOut]:
    result = await db.execute(select(DocB).where(DocB.site_id == site_id))
    return [DocBOut.model_validate(d) for d in result.scalars().all()]


@router.patch("/doc-b/{doc_b_id}", response_model=DocBOut)
async def update_doc_b(
    doc_b_id: uuid.UUID,
    payload: DocBUpdate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> DocBOut:
    result = await db.execute(select(DocB).where(DocB.id == doc_b_id))
    doc_b = result.scalar_one_or_none()
    if doc_b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doc B introuvable")

    changes = payload.model_dump(exclude_unset=True)
    for field, new_value in changes.items():
        old_value = getattr(doc_b, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="doc_b", entity_id=doc_b.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(doc_b, field, new_value)

    await db.commit()
    await db.refresh(doc_b)
    return DocBOut.model_validate(doc_b)


@router.delete("/doc-b/{doc_b_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc_b(
    doc_b_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Suppression réelle (pas de colonne deleted_at sur doc_b — voir models/tracking.py).
    Le Document lui-même (fichier + versions) n'est pas touché, seul le lien administratif l'est."""
    result = await db.execute(select(DocB).where(DocB.id == doc_b_id))
    doc_b = result.scalar_one_or_none()
    if doc_b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doc B introuvable")
    await log_audit(db, user_id=current_user.id, entity="doc_b", entity_id=doc_b.id, action="DELETE")
    await db.delete(doc_b)
    await db.commit()


# ------------------------------------------------------------------
# APS
# ------------------------------------------------------------------
@router.post("/sites/{site_id}/aps", response_model=ApsOut, status_code=status.HTTP_201_CREATED)
async def create_aps(
    site_id: uuid.UUID,
    payload: ApsCreate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ApsOut:
    await _get_site_or_404(db, site_id)
    if payload.aps_type not in VALID_APS_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Type APS invalide. Valeurs acceptées : {sorted(VALID_APS_TYPES)}",
        )

    aps = ApsDocument(
        site_id=site_id,
        aps_type=payload.aps_type,
        version=payload.version or 1,
        document_id=payload.document_id,
        observation=payload.observation,
        created_at=datetime.now(timezone.utc),
    )
    db.add(aps)
    await db.flush()
    await log_audit(
        db, user_id=current_user.id, entity="aps_documents", entity_id=aps.id,
        action="CREATE", new_value=aps.aps_type,
    )
    await db.commit()
    await db.refresh(aps)
    return ApsOut.model_validate(aps)


@router.get("/sites/{site_id}/aps", response_model=list[ApsOut])
async def list_aps(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApsOut]:
    result = await db.execute(
        select(ApsDocument).where(ApsDocument.site_id == site_id).order_by(ApsDocument.created_at.desc())
    )
    return [ApsOut.model_validate(a) for a in result.scalars().all()]


@router.patch("/aps/{aps_id}", response_model=ApsOut)
async def update_aps(
    aps_id: uuid.UUID,
    payload: ApsUpdate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ApsOut:
    result = await db.execute(select(ApsDocument).where(ApsDocument.id == aps_id))
    aps = result.scalar_one_or_none()
    if aps is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "APS introuvable")

    changes = payload.model_dump(exclude_unset=True)
    if "aps_type" in changes and changes["aps_type"] not in VALID_APS_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type APS invalide")

    for field, new_value in changes.items():
        old_value = getattr(aps, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="aps_documents", entity_id=aps.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(aps, field, new_value)

    await db.commit()
    await db.refresh(aps)
    return ApsOut.model_validate(aps)


@router.delete("/aps/{aps_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aps(
    aps_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(ApsDocument).where(ApsDocument.id == aps_id))
    aps = result.scalar_one_or_none()
    if aps is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "APS introuvable")
    await log_audit(db, user_id=current_user.id, entity="aps_documents", entity_id=aps.id, action="DELETE")
    await db.delete(aps)
    await db.commit()
