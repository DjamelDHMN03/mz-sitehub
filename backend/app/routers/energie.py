from datetime import date
from pathlib import Path
import re
from typing import Literal
from uuid import UUID

from docx import Document
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/api/energie", tags=["Energie"])

# Depuis backend/app/routers/energie.py, parents[2] correspond à backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = (
    BACKEND_DIR
    / "storage"
    / "templates"
    / "Demande de Raccordement en Energie Electrique Client FSM BIS.docx"
)
OUTPUT_DIR = BACKEND_DIR / "storage" / "demandes_sonelgaz"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PLACEHOLDER_DOTS = "………………………"

class SiteEnergiePayload(BaseModel):
    mode: Literal["SONELGAZ", "SOUS_COMPTAGE"] = "SONELGAZ"

    demande_deposee: bool = False
    demande_deposee_le: date | None = None
    etude_effectuee: bool = False
    etude_effectuee_le: date | None = None
    devis_paye: bool = False
    devis_paye_le: date | None = None
    site_raccorde: bool = False
    site_raccorde_le: date | None = None

    sous_comptage_permanent: bool = False

    provisoire_actif: bool = False
    provisoire_debut: date | None = None
    provisoire_fin: date | None = None
    montant_mensuel: int = Field(default=18000, ge=0)

    necessite_extension: bool = False
    aps_pret: bool = False
    plan_situation_pret: bool = False
    demande_sonelgaz_prete: bool = False
    observation: str | None = None

class PaiementPayload(BaseModel):
    mois: date
    date_paiement: date = Field(default_factory=date.today)
    montant: int = Field(default=18000, ge=0)
    observation: str | None = None

async def _verifier_site(db: AsyncSession, site_id: UUID) -> None:
    result = await db.execute(
        select(Site.id).where(
            Site.id == site_id,
            Site.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Site introuvable.")

@router.get("/sites")
async def lister_sites_energie(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("sites", "read")),
):
    result = await db.execute(text("""
        SELECT
            s.id AS site_id,
            s.code AS code_site,
            s.name AS nom_site,
            s.address AS adresse,
            s.owner_name AS proprietaire,
            ST_X(s.geom) AS longitude,
            ST_Y(s.geom) AS latitude,
            COALESCE(e.mode, 'SONELGAZ') AS mode,
            COALESCE(e.demande_deposee, false) AS demande_deposee,
            e.demande_deposee_le,
            COALESCE(e.etude_effectuee, false) AS etude_effectuee,
            e.etude_effectuee_le,
            COALESCE(e.devis_paye, false) AS devis_paye,
            e.devis_paye_le,
            COALESCE(e.site_raccorde, false) AS site_raccorde,
            e.site_raccorde_le,
            COALESCE(e.sous_comptage_permanent, false) AS sous_comptage_permanent,
            COALESCE(e.provisoire_actif, false) AS provisoire_actif,
            e.provisoire_debut,
            e.provisoire_fin,
            COALESCE(e.montant_mensuel, 18000) AS montant_mensuel,
            COALESCE(e.necessite_extension, false) AS necessite_extension,
            COALESCE(e.aps_pret, false) AS aps_pret,
            COALESCE(e.plan_situation_pret, false) AS plan_situation_pret,
            COALESCE(e.demande_sonelgaz_prete, false) AS demande_sonelgaz_prete,
            e.observation
        FROM public.sites AS s
        LEFT JOIN public.site_energy AS e ON e.site_id = s.id
        WHERE s.deleted_at IS NULL
        ORDER BY s.code
    """))
    return [dict(row) for row in result.mappings().all()]

@router.put("/sites/{site_id}")
async def enregistrer_suivi_energie(
    site_id: UUID,
    payload: SiteEnergiePayload,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("sites", "write")),
):
    await _verifier_site(db, site_id)
    values = payload.model_dump()
    values["site_id"] = site_id

    await db.execute(text("""
        INSERT INTO public.site_energy (
            site_id, mode,
            demande_deposee, demande_deposee_le,
            etude_effectuee, etude_effectuee_le,
            devis_paye, devis_paye_le,
            site_raccorde, site_raccorde_le,
            sous_comptage_permanent,
            provisoire_actif, provisoire_debut, provisoire_fin, montant_mensuel,
            necessite_extension, aps_pret, plan_situation_pret,
            demande_sonelgaz_prete, observation
        ) VALUES (
            :site_id, :mode,
            :demande_deposee, :demande_deposee_le,
            :etude_effectuee, :etude_effectuee_le,
            :devis_paye, :devis_paye_le,
            :site_raccorde, :site_raccorde_le,
            :sous_comptage_permanent,
            :provisoire_actif, :provisoire_debut, :provisoire_fin, :montant_mensuel,
            :necessite_extension, :aps_pret, :plan_situation_pret,
            :demande_sonelgaz_prete, :observation
        )
        ON CONFLICT (site_id) DO UPDATE SET
            mode = EXCLUDED.mode,
            demande_deposee = EXCLUDED.demande_deposee,
            demande_deposee_le = EXCLUDED.demande_deposee_le,
            etude_effectuee = EXCLUDED.etude_effectuee,
            etude_effectuee_le = EXCLUDED.etude_effectuee_le,
            devis_paye = EXCLUDED.devis_paye,
            devis_paye_le = EXCLUDED.devis_paye_le,
            site_raccorde = EXCLUDED.site_raccorde,
            site_raccorde_le = EXCLUDED.site_raccorde_le,
            sous_comptage_permanent = EXCLUDED.sous_comptage_permanent,
            provisoire_actif = EXCLUDED.provisoire_actif,
            provisoire_debut = EXCLUDED.provisoire_debut,
            provisoire_fin = EXCLUDED.provisoire_fin,
            montant_mensuel = EXCLUDED.montant_mensuel,
            necessite_extension = EXCLUDED.necessite_extension,
            aps_pret = EXCLUDED.aps_pret,
            plan_situation_pret = EXCLUDED.plan_situation_pret,
            demande_sonelgaz_prete = EXCLUDED.demande_sonelgaz_prete,
            observation = EXCLUDED.observation,
            updated_at = now()
    """), values)
    await db.commit()
    return {"site_id": str(site_id), **payload.model_dump(mode="json")}

@router.get("/sites/{site_id}/paiements")
async def lister_paiements(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("sites", "read")),
):
    await _verifier_site(db, site_id)
    result = await db.execute(
        text("""
            SELECT id, site_id, mois, date_paiement, montant, observation, created_at
            FROM public.site_energy_payments
            WHERE site_id = :site_id
            ORDER BY mois DESC
        """),
        {"site_id": site_id},
    )
    return [dict(row) for row in result.mappings().all()]

@router.post("/sites/{site_id}/paiements")
async def enregistrer_paiement(
    site_id: UUID,
    payload: PaiementPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sites", "write")),
):
    await _verifier_site(db, site_id)
    if payload.mois.day != 1:
        raise HTTPException(
            status_code=422,
            detail="Le champ mois doit être le premier jour du mois concerné.",
        )

    result = await db.execute(
        text("""
            INSERT INTO public.site_energy_payments
                (site_id, mois, date_paiement, montant, observation, created_by)
            VALUES
                (:site_id, :mois, :date_paiement, :montant, :observation, :created_by)
            ON CONFLICT (site_id, mois) DO UPDATE SET
                date_paiement = EXCLUDED.date_paiement,
                montant = EXCLUDED.montant,
                observation = EXCLUDED.observation
            RETURNING id, site_id, mois, date_paiement, montant, observation, created_at
        """),
        {
            "site_id": site_id,
            "mois": payload.mois,
            "date_paiement": payload.date_paiement,
            "montant": payload.montant,
            "observation": payload.observation,
            "created_by": current_user.id,
        },
    )
    paiement = dict(result.mappings().one())
    await db.commit()
    return paiement
