"""
Routeur /ooredoo-centre — Dashboard Suivi Ooredoo Centre.

Toutes les routes sont protégées par get_current_user (authentification JWT).
La synchronisation est réservée aux rôles possédant la permission "sites/write".
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/ooredoo-centre", tags=["ooredoo-centre"])

# Chemin absolu vers le script d'import (racine backend)
_IMPORT_SCRIPT = Path(__file__).resolve().parents[2] / "import_suivi_centre.py"


# ------------------------------------------------------------------
# 1. KPIs globaux
# ------------------------------------------------------------------
@router.get("/stats", summary="KPIs dashboard Ooredoo Centre")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    kpi_row = (
        await db.execute(text("SELECT * FROM v_dashboard_ooredoo_centre"))
    ).mappings().first()

    wilaya_rows = (
        await db.execute(text("SELECT * FROM v_sites_par_wilaya"))
    ).mappings().all()

    return {
        "kpis": dict(kpi_row) if kpi_row else {},
        "par_wilaya": [dict(r) for r in wilaya_rows],
    }


# ------------------------------------------------------------------
# 2. Performance par négociateur
# ------------------------------------------------------------------
@router.get("/negociateurs", summary="Stats par négociateur")
async def get_negociateurs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(text("SELECT * FROM v_stats_negociateurs"))
    ).mappings().all()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# 3. Liste des sites filtrée et paginée
# ------------------------------------------------------------------
@router.get("/sites", summary="Liste des sites Ooredoo Centre filtrée")
async def list_sites(
    progress_category: Optional[str] = Query(
        None, description="BOUCLE | EN_COURS | BLOQUE"
    ),
    progress_stage: Optional[str] = Query(None, description="CCT, TSS, DOC_B…"),
    negotiator: Optional[str] = Query(None, description="Nom (recherche partielle)"),
    wilaya: Optional[str] = Query(None, description="Nom wilaya (recherche partielle)"),
    project: Optional[str] = Query(None, description="ROLLOUT, STRATEGIC, B2B…"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conditions = ["s.deleted_at IS NULL", "s.project IS NOT NULL"]
    params: dict = {}

    if progress_category:
        conditions.append("s.progress_category = :progress_category")
        params["progress_category"] = progress_category.upper()

    if progress_stage:
        conditions.append("s.progress_stage = :progress_stage")
        params["progress_stage"] = progress_stage.upper()

    if negotiator:
        conditions.append("n.name ILIKE :negotiator")
        params["negotiator"] = f"%{negotiator}%"

    if wilaya:
        conditions.append("(w.name ILIKE :wilaya OR s.commune_name ILIKE :wilaya)")
        params["wilaya"] = f"%{wilaya}%"

    if project:
        conditions.append("s.project ILIKE :project")
        params["project"] = f"%{project}%"

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    sql_count = text(f"""
        SELECT COUNT(s.id)
        FROM sites s
        LEFT JOIN negotiators n ON s.negotiator_id = n.id
        LEFT JOIN wilayas w ON s.wilaya_id = w.id
        WHERE {where}
    """)

    sql_items = text(f"""
        SELECT
            s.id, s.code, s.owner_name, s.commune_name,
            w.name            AS wilaya_name,
            s.wilaya_id,
            n.name            AS negociateur_nom,
            n.kind            AS negociateur_type,
            s.project,
            s.progress_category,
            s.progress_stage,
            s.progress_raw,
            s.waiting_for,
            s.rent_negotiated,
            s.doc_a_date,
            s.doc_b_date,
            s.doc_b_delay_days,
            s.tss_date,
            s.contract_date,
            s.site_typology,
            s.site_model,
            s.owner_type,
            s.observation,
            s.updated_at
        FROM sites s
        LEFT JOIN negotiators n ON s.negotiator_id = n.id
        LEFT JOIN wilayas w ON s.wilaya_id = w.id
        WHERE {where}
        ORDER BY s.progress_category ASC, s.code ASC
        LIMIT :limit OFFSET :offset
    """)

    total = (await db.execute(sql_count, params)).scalar_one()
    rows = (await db.execute(sql_items, params)).mappings().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [dict(r) for r in rows],
    }


# ------------------------------------------------------------------
# 4. Synchronisation depuis le fichier Excel (ADMIN / MANAGER)
# ------------------------------------------------------------------
@router.post(
    "/sync",
    summary="Synchroniser depuis SUIVI_NETTOYE.xlsx (ADMIN/MANAGER)",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_sync(
    current_user: User = Depends(require_permission("sites", "write")),
) -> dict:
    """
    Relance import_suivi_centre.py --apply en sous-processus.
    Le fichier SUIVI_NETTOYE.xlsx doit être présent dans le dossier backend.
    La requête retourne immédiatement (202) ; l'import tourne en arrière-plan.
    """
    xlsx = _IMPORT_SCRIPT.parent / "SUIVI_NETTOYE.xlsx"
    if not xlsx.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SUIVI_NETTOYE.xlsx introuvable dans le dossier backend.",
        )

    async def _run():
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(_IMPORT_SCRIPT), str(xlsx), "--apply",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode("utf-8", errors="replace")

    # Lance sans bloquer la réponse HTTP
    asyncio.create_task(_run())

    return {
        "status": "accepted",
        "message": "Synchronisation lancée en arrière-plan. Rafraîchissez dans 30 secondes.",
    }
