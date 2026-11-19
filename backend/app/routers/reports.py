"""
Routeur Rapports / Exports (sections 77-79, 95).
"""
import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.contact import Contact
from app.models.site import Site, SiteStatus, Wilaya
from app.models.task import Task
from app.models.tracking import Contract
from app.models.document import Document
from app.models.user import User
from app.services.export import site_fiche_pdf, sites_to_csv, sites_to_xlsx
from app.services.share import build_zip_archive
from app.services.storage import get_storage_provider

router = APIRouter(prefix="/reports", tags=["reports"])

SITE_EXPORT_COLUMNS = ["code", "name", "wilaya", "status", "owner_name", "organisme", "created_at"]
SITE_EXPORT_HEADERS = {
    "code": "Code", "name": "Nom", "wilaya": "Wilaya", "status": "Statut",
    "owner_name": "Propriétaire", "organisme": "Organisme", "created_at": "Date création",
}


async def _fetch_filtered_sites(
    db: AsyncSession,
    wilaya_id: int | None,
    status_id: int | None,
    organisme: str | None,
    created_after: date | None,
) -> list[dict]:
    stmt = (
        select(Site, SiteStatus.label, Wilaya.name)
        .join(SiteStatus, Site.status_id == SiteStatus.id)
        .outerjoin(Wilaya, Site.wilaya_id == Wilaya.id)
        .where(Site.deleted_at.is_(None))
    )
    if wilaya_id:
        stmt = stmt.where(Site.wilaya_id == wilaya_id)
    if status_id:
        stmt = stmt.where(Site.status_id == status_id)
    if organisme:
        stmt = stmt.where(Site.organisme.ilike(f"%{organisme}%"))
    if created_after:
        stmt = stmt.where(Site.created_at >= created_after)

    result = await db.execute(stmt)
    rows = []
    for site, status_label, wilaya_name in result.all():
        rows.append({
            "code": site.code, "name": site.name, "wilaya": wilaya_name,
            "status": status_label, "owner_name": site.owner_name,
            "organisme": site.organisme, "created_at": site.created_at.strftime("%Y-%m-%d"),
        })
    return rows


@router.get("/sites/export")
async def export_sites_report(
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    wilaya_id: int | None = None,
    status_id: int | None = None,
    organisme: str | None = None,
    created_after: date | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    rows = await _fetch_filtered_sites(db, wilaya_id, status_id, organisme, created_after)

    if format == "csv":
        content = sites_to_csv(rows, SITE_EXPORT_COLUMNS)
        media_type, filename = "text/csv", "rapport_sites.csv"
    else:
        content = sites_to_xlsx(rows, SITE_EXPORT_COLUMNS, SITE_EXPORT_HEADERS)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "rapport_sites.xlsx"

    return Response(
        content=content, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sites/{site_id}/fiche-pdf")
async def export_site_fiche_pdf(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Fiche PDF complète d'un site (section 78)."""
    result = await db.execute(
        select(Site, SiteStatus.label, Wilaya.name)
        .join(SiteStatus, Site.status_id == SiteStatus.id)
        .outerjoin(Wilaya, Site.wilaya_id == Wilaya.id)
        .where(Site.id == site_id, Site.deleted_at.is_(None))
    )
    row = result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")
    site, status_label, wilaya_name = row

    contacts_result = await db.execute(select(Contact).where(Contact.site_id == site_id, Contact.deleted_at.is_(None)))
    documents_result = await db.execute(select(Document).where(Document.site_id == site_id, Document.deleted_at.is_(None)))
    contracts_result = await db.execute(select(Contract).where(Contract.site_id == site_id, Contract.deleted_at.is_(None)))
    actions_result = await db.execute(select(Task).where(Task.site_id == site_id))

    site_dict = {
        "code": site.code, "name": site.name, "wilaya": wilaya_name, "commune": None,
        "address": site.address, "latitude": None, "longitude": None,
        "owner_name": site.owner_name, "organisme": site.organisme, "status_label": status_label,
    }
    contacts = [{"first_name": c.first_name, "last_name": c.last_name, "role_label": c.role_label, "phone": c.phone}
                for c in contacts_result.scalars().all()]
    documents = [{"filename": d.filename, "category": d.category, "version": d.version}
                 for d in documents_result.scalars().all()]
    contracts = [{"reference": c.reference, "status": c.status, "amount": c.amount}
                 for c in contracts_result.scalars().all()]
    actions = [{"title": t.title, "due_date": t.due_date.isoformat() if t.due_date else None, "status": t.status}
               for t in actions_result.scalars().all()]

    # Chemin robuste : fonctionne aussi bien en local (hors Docker) qu'en
    # conteneur, plutôt que de figer "/app/assets/..." qui n'existe qu'à
    # l'intérieur du conteneur backend.
    logo_mz = "/app/assets/logos/Logo_MZ_BUILDING.png"
    logo_ooredoo = "/app/assets/logos/Logo_OOREDOO.png"
    if not os.path.exists(logo_mz):
        logo_mz = None
    if not os.path.exists(logo_ooredoo):
        logo_ooredoo = None

    pdf_bytes = site_fiche_pdf(
        site_dict, contacts, documents, contracts, actions,
        logo_mz_path=logo_mz,
        logo_ooredoo_path=logo_ooredoo,
    )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fiche_{site.code}.pdf"'},
    )


@router.get("/sites/{site_id}/export-complet")
async def export_site_complete(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export dossier complet en ZIP (section 79) : tous les documents +
    la fiche PDF récapitulative."""
    result = await db.execute(select(Site).where(Site.id == site_id, Site.deleted_at.is_(None)))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")

    storage = get_storage_provider()
    doc_result = await db.execute(select(Document).where(Document.site_id == site_id, Document.deleted_at.is_(None)))
    documents = doc_result.scalars().all()

    files: list[tuple[str, bytes]] = []
    for d in documents:
        try:
            content = storage.read(d.storage_key)
            files.append((f"{d.category}/{d.filename}", content))
        except FileNotFoundError:
            continue  # fichier manquant sur le disque — ignoré plutôt que de faire échouer tout l'export

    # Inclut la fiche PDF récapitulative dans le ZIP
    fiche_response = await export_site_fiche_pdf(site_id, current_user, db)
    files.append((f"{site.code}_FICHE.pdf", fiche_response.body))

    zip_bytes = build_zip_archive(files)
    return Response(
        content=zip_bytes, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{site.code}_COMPLETE.zip"'},
    )
