"""
Routeur /site-statuses — lecture seule pour l'instant (la gestion ADMIN
d'ajout/modification/réorganisation, section 53, arrivera avec le module
Paramètres). Nécessaire dès maintenant car le frontend doit afficher le
vrai libellé/couleur de chaque statut plutôt qu'un id brut.
"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.site import SiteStatus
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/site-statuses", tags=["site-statuses"])


class SiteStatusOut(BaseModel):
    id: int
    code: str
    label: str
    color: str
    sort_order: int

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SiteStatusOut])
async def list_site_statuses(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SiteStatusOut]:
    # Section 84 (optimisation) : les statuts changent rarement (ADMIN
    # uniquement, section 53) — cache navigateur court pour éviter un
    # aller-retour DB à chaque écran qui affiche un badge de statut.
    response.headers["Cache-Control"] = "private, max-age=60"
    result = await db.execute(
        select(SiteStatus).where(SiteStatus.is_active.is_(True)).order_by(SiteStatus.sort_order)
    )
    return [SiteStatusOut.model_validate(s) for s in result.scalars().all()]
