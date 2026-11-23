"""
Routeur /site-visits — TSS (Technical Site Survey) et CCT (Commission de Choix
de Terrain) affichees dans le Calendrier.
"""
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.site import Site
from app.models.site_visit import VALID_VISIT_TYPES, SiteVisit
from app.models.user import User
from app.schemas.site_visit import (
    SiteOption,
    SiteVisitCreate,
    SiteVisitOut,
    SiteVisitUpdate,
)

router = APIRouter(prefix="/site-visits", tags=["site-visits"])

TEXT_FIELDS = [
    "location", "bet_name", "radio_engineer_name", "civil_work_name",
    "transmission_name", "negotiator_name", "observation",
]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _check_type(value: str) -> str:
    visit_type = value.strip().upper()
    if visit_type not in VALID_VISIT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Type invalide : {sorted(VALID_VISIT_TYPES)}")
    return visit_type


async def _find_site(db: AsyncSession, code: str):
    row = (
        await db.execute(
            select(Site.id, Site.code).where(
                func.upper(Site.code) == code.strip().upper(),
                Site.deleted_at.is_(None),
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Code site inconnu : {code.strip()}")
    return row


@router.get("/site-options", response_model=list[SiteOption])
async def list_site_options(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SiteOption]:
    """Codes des sites (+ nom du negociateur) pour les listes de saisie."""
    sites = (
        await db.execute(
            select(Site.code, Site.responsible_user_id)
            .where(Site.deleted_at.is_(None))
            .order_by(Site.code)
        )
    ).all()
    users = (await db.execute(select(User).where(User.deleted_at.is_(None)))).scalars().all()
    names = {u.id: u.full_name for u in users}
    return [SiteOption(code=code, responsible_name=names.get(resp)) for code, resp in sites]


@router.get("", response_model=list[SiteVisitOut])
async def list_site_visits(
    date_from: date | None = None,
    date_to: date | None = None,
    visit_type: str | None = None,
    site_code: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SiteVisitOut]:
    stmt = select(SiteVisit)
    if date_from:
        stmt = stmt.where(SiteVisit.visit_date >= date_from)
    if date_to:
        stmt = stmt.where(SiteVisit.visit_date <= date_to)
    if visit_type:
        stmt = stmt.where(SiteVisit.visit_type == visit_type.strip().upper())
    if site_code:
        stmt = stmt.where(func.upper(SiteVisit.site_code) == site_code.strip().upper())
    stmt = stmt.order_by(SiteVisit.visit_date, SiteVisit.visit_type, SiteVisit.created_at).limit(1000)
    result = await db.execute(stmt)
    return [SiteVisitOut.model_validate(v) for v in result.scalars().all()]


@router.post("", response_model=SiteVisitOut, status_code=status.HTTP_201_CREATED)
async def create_site_visit(
    payload: SiteVisitCreate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> SiteVisitOut:
    visit_type = _check_type(payload.visit_type)
    site = await _find_site(db, payload.site_code)

    texts = {f: _clean(getattr(payload, f)) for f in TEXT_FIELDS}
    if visit_type == "CCT":
        texts["radio_engineer_name"] = None  # pas d'ingenieur radio pour une CCT

    now = datetime.now(timezone.utc)
    visit = SiteVisit(
        visit_type=visit_type,
        visit_date=payload.visit_date,
        site_id=site.id,
        site_code=site.code,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
        **texts,
    )
    db.add(visit)
    await db.flush()
    await log_audit(
        db, user_id=current_user.id, entity="site_visits", entity_id=visit.id,
        action="CREATE", new_value=f"{visit_type} {site.code} {payload.visit_date}",
    )
    await db.commit()
    await db.refresh(visit)
    return SiteVisitOut.model_validate(visit)


@router.patch("/{visit_id}", response_model=SiteVisitOut)
async def update_site_visit(
    visit_id: uuid.UUID,
    payload: SiteVisitUpdate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> SiteVisitOut:
    visit = (await db.execute(select(SiteVisit).where(SiteVisit.id == visit_id))).scalar_one_or_none()
    if visit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "TSS / CCT introuvable")

    changes = payload.model_dump(exclude_unset=True)
    for required in ("visit_type", "visit_date", "site_code"):
        if required in changes and changes[required] is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Le champ '{required}' est obligatoire")

    if "visit_type" in changes:
        changes["visit_type"] = _check_type(changes["visit_type"])
    if "site_code" in changes:
        site = await _find_site(db, changes["site_code"])
        changes["site_code"] = site.code
        changes["site_id"] = site.id
    for f in TEXT_FIELDS:
        if f in changes:
            changes[f] = _clean(changes[f])
    if changes.get("visit_type", visit.visit_type) == "CCT":
        changes["radio_engineer_name"] = None

    for field, new_value in changes.items():
        old_value = getattr(visit, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="site_visits", entity_id=visit.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(visit, field, new_value)

    visit.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(visit)
    return SiteVisitOut.model_validate(visit)


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site_visit(
    visit_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> None:
    visit = (await db.execute(select(SiteVisit).where(SiteVisit.id == visit_id))).scalar_one_or_none()
    if visit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "TSS / CCT introuvable")
    await log_audit(
        db, user_id=current_user.id, entity="site_visits", entity_id=visit.id,
        action="DELETE", old_value=f"{visit.visit_type} {visit.site_code} {visit.visit_date}",
    )
    await db.delete(visit)
    await db.commit()
