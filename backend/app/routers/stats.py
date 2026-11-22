"""Routeur /stats - statistiques par negociateur (responsable de site)."""
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.site import Site, SiteStatus
from app.models.tracking import Contract
from app.models.user import Role, User
from app.routers.dashboard import STATUS_GROUPS

router = APIRouter(prefix="/stats", tags=["stats"])

# ADMIN et MANAGER voient tous les negociateurs ; les autres roles ne voient que leurs chiffres
FULL_VIEW_ROLES = {"ADMIN", "MANAGER"}

# Memes regroupements de statuts que le dashboard (source unique : STATUS_GROUPS)
CATEGORIES = {
    "en_cours": STATUS_GROUPS["en_cours"],
    "negociation": STATUS_GROUPS["negociation"],
    "valides": STATUS_GROUPS["signes"] + STATUS_GROUPS["operationnels"],
    "bloques": STATUS_GROUPS["bloques"],
}


class NegociateurStats(BaseModel):
    user_id: uuid.UUID | None
    full_name: str
    assignes: int
    en_cours: int
    negociation: int
    valides: int
    bloques: int
    contrats_signes: int


@router.get("/negociateurs", response_model=list[NegociateurStats])
async def negociateurs_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NegociateurStats]:
    role_code = (
        await db.execute(select(Role.code).where(Role.id == current_user.role_id))
    ).scalar_one_or_none()
    sees_all = role_code in FULL_VIEW_ROLES

    rows = (
        await db.execute(
            select(Site.responsible_user_id, SiteStatus.code, func.count(Site.id))
            .join(SiteStatus, Site.status_id == SiteStatus.id)
            .where(Site.deleted_at.is_(None))
            .group_by(Site.responsible_user_id, SiteStatus.code)
        )
    ).all()

    per_user: dict = defaultdict(lambda: defaultdict(int))
    for user_id, code, n in rows:
        per_user[user_id][code] += n

    signed_rows = (
        await db.execute(
            select(Site.responsible_user_id, func.count(Contract.id))
            .join(Site, Site.id == Contract.site_id)
            .where(
                Site.deleted_at.is_(None),
                Contract.deleted_at.is_(None),
                Contract.date_signed.is_not(None),
            )
            .group_by(Site.responsible_user_id)
        )
    ).all()
    signed_by_user = {uid: n for uid, n in signed_rows}

    def build(user_id, name: str) -> NegociateurStats:
        counts = per_user.get(user_id, {})
        data = {k: sum(counts.get(c, 0) for c in codes) for k, codes in CATEGORIES.items()}
        return NegociateurStats(
            user_id=user_id, full_name=name, assignes=sum(counts.values()), contrats_signes=signed_by_user.get(user_id, 0), **data
        )

    users = (
        await db.execute(
            select(User)
            .where(User.is_active.is_(True), User.deleted_at.is_(None))
            .order_by(User.first_name, User.last_name)
        )
    ).scalars().all()

    result: list[NegociateurStats] = []
    for u in users:
        item = build(u.id, u.full_name)
        if u.id == current_user.id or (sees_all and item.assignes > 0):
            result.append(item)
    if sees_all and None in per_user:
        result.append(build(None, "Non assign\u00e9"))
    return result