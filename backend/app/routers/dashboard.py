"""
Routeur /dashboard — statistiques temps réel (section 13 du cahier des charges).

Principe : chaque chiffre est calculé à partir de données réellement enregistrées.
Deux indicateurs de la section 13 dépendent de modules pas encore construits
("À relancer" -> Contacts/Phase 10, "Dossiers incomplets" -> Checklist/Phase 12+) :
plutôt que de les approximer avec une logique inventée, l'API renvoie
`available: false` et le frontend affiche "à venir" — cohérent avec la règle
"ne jamais inventer une donnée" (section 74/118) appliquée aux métriques elles-mêmes.
"""
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.site import Site, SiteStatus
from app.models.tracking import Contract, DocB
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Regroupement des codes de statut en catégories affichées sur le dashboard.
# Basé exactement sur les 23 statuts créés en Phase 2 (migration 001).
STATUS_GROUPS: dict[str, list[str]] = {
    "nouveaux": ["NOUVEAU", "RECHERCHE_TERRAIN"],
    "en_cours": [
        "PROPOSITION", "DOCB_A_PREPARER", "DOCB_DEPOSE", "ACCORD_PRINCIPE",
        "ATTENTE_DOCUMENTS", "APS_DEMANDE", "APS_RECU", "VALIDATION_RADIO",
        "AUTORISATION_EN_COURS", "CONTRAT_PREPARATION", "CONTRAT_ENVOYE",
        "INSTALLATION_AUTORISEE", "TRAVAUX_EN_COURS",
    ],
    "negociation": ["NEGOCIATION", "CONTRAT_SIGNATURE"],
    "bloques": ["BLOQUE"],
    "signes": ["CONTRAT_SIGNE"],
    "operationnels": ["OPERATIONNEL"],
    "refuses": ["REFUSE", "ABANDONNE", "ARCHIVE"],
}


class MetricValue(BaseModel):
    value: int
    available: bool = True
    note: str | None = None


class DashboardStats(BaseModel):
    total_sites: MetricValue
    nouveaux: MetricValue
    en_cours: MetricValue
    negociation: MetricValue
    bloques: MetricValue
    signes: MetricValue
    operationnels: MetricValue
    refuses: MetricValue
    a_relancer: MetricValue
    contrats_a_signer: MetricValue
    aps_en_attente: MetricValue
    doc_b_manquants: MetricValue
    dossiers_incomplets: MetricValue


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    # --- Comptage par code de statut (une seule requête groupée) ---
    result = await db.execute(
        select(SiteStatus.code, func.count(Site.id))
        .join(Site, Site.status_id == SiteStatus.id)
        .where(Site.deleted_at.is_(None))
        .group_by(SiteStatus.code)
    )
    counts_by_code: dict[str, int] = dict(result.all())

    def group_count(codes: list[str]) -> int:
        return sum(counts_by_code.get(code, 0) for code in codes)

    total_sites = sum(counts_by_code.values())

    # --- Contrats à signer : envoyés mais pas encore signés ---
    contracts_a_signer = (
        await db.execute(
            select(func.count(Contract.id)).where(
                Contract.deleted_at.is_(None),
                Contract.date_sent.is_not(None),
                Contract.date_signed.is_(None),
            )
        )
    ).scalar_one()

    # --- APS en attente : sites au statut APS_DEMANDE ---
    aps_en_attente = counts_by_code.get("APS_DEMANDE", 0)

    # --- Doc B manquants : sites actifs sans AUCUN enregistrement doc_b ---
    doc_b_manquants = (
        await db.execute(
            select(func.count(Site.id)).where(
                Site.deleted_at.is_(None),
                ~Site.id.in_(select(DocB.site_id)),
            )
        )
    ).scalar_one()

    return DashboardStats(
        total_sites=MetricValue(value=total_sites),
        nouveaux=MetricValue(value=group_count(STATUS_GROUPS["nouveaux"])),
        en_cours=MetricValue(value=group_count(STATUS_GROUPS["en_cours"])),
        negociation=MetricValue(value=group_count(STATUS_GROUPS["negociation"])),
        bloques=MetricValue(value=group_count(STATUS_GROUPS["bloques"])),
        signes=MetricValue(value=group_count(STATUS_GROUPS["signes"])),
        operationnels=MetricValue(value=group_count(STATUS_GROUPS["operationnels"])),
        refuses=MetricValue(value=group_count(STATUS_GROUPS["refuses"])),
        contrats_a_signer=MetricValue(value=contracts_a_signer),
        aps_en_attente=MetricValue(value=aps_en_attente),
        doc_b_manquants=MetricValue(value=doc_b_manquants),
        a_relancer=MetricValue(
            value=0, available=False,
            note="Nécessite le module Contacts (Phase 10) — relance basée sur next_followup_at",
        ),
        dossiers_incomplets=MetricValue(
            value=0, available=False,
            note="Nécessite la checklist par site (Phase 12+, section 107-108)",
        ),
    )
