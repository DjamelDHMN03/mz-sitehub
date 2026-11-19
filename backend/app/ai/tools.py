"""
Tools MZ ASSISTANT (sections 62-65, 71-72). Chaque fonction interroge
directement la base et renvoie une structure de données — jamais un texte
généré par le LLM. Le LLM (ou l'analyseur d'intention déterministe) ne fait
que CHOISIR quel tool appeler et avec quels paramètres ; la donnée qui
revient à l'utilisateur vient toujours d'une de ces fonctions (section 66 :
distinguer DONNÉE ENREGISTRÉE et INTERPRÉTATION IA).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.document import Document
from app.models.site import Site, SiteStatus, Wilaya
from app.models.tracking import ApsDocument, Contract, DocB


async def tool_list_sites_by_status(db: AsyncSession, status_code: str) -> list[dict]:
    result = await db.execute(
        select(Site.code, Site.name)
        .join(SiteStatus, Site.status_id == SiteStatus.id)
        .where(SiteStatus.code == status_code, Site.deleted_at.is_(None))
    )
    return [{"code": code, "name": name} for code, name in result.all()]


async def tool_list_sites_by_wilaya(db: AsyncSession, wilaya_name: str) -> list[dict]:
    result = await db.execute(
        select(Site.code, Site.name)
        .join(Wilaya, Site.wilaya_id == Wilaya.id)
        .where(Wilaya.name.ilike(wilaya_name), Site.deleted_at.is_(None))
    )
    return [{"code": code, "name": name} for code, name in result.all()]


async def tool_list_sites_without_gps(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Site.code, Site.name).where(Site.geom.is_(None), Site.deleted_at.is_(None))
    )
    return [{"code": code, "name": name} for code, name in result.all()]


async def tool_list_sites_missing_aps(db: AsyncSession, wilaya_name: str | None) -> list[dict]:
    stmt = (
        select(Site.code, Site.name)
        .where(Site.deleted_at.is_(None), ~Site.id.in_(select(ApsDocument.site_id)))
    )
    if wilaya_name:
        stmt = stmt.join(Wilaya, Site.wilaya_id == Wilaya.id).where(Wilaya.name.ilike(wilaya_name))
    result = await db.execute(stmt)
    return [{"code": code, "name": name} for code, name in result.all()]


async def tool_summarize_site(db: AsyncSession, code: str) -> dict | None:
    result = await db.execute(
        select(Site, SiteStatus.label)
        .join(SiteStatus, Site.status_id == SiteStatus.id)
        .where(Site.code == code, Site.deleted_at.is_(None))
    )
    row = result.first()
    if row is None:
        return None
    site, status_label = row

    contacts_result = await db.execute(select(Contact).where(Contact.site_id == site.id, Contact.deleted_at.is_(None)))
    contacts = [
        {"name": f"{c.first_name or ''} {c.last_name or ''}".strip() or "À COMPLÉTER", "role": c.role_label}
        for c in contacts_result.scalars().all()
    ]

    return {
        "code": site.code,
        "name": site.name,
        "status": status_label,
        "owner_name": site.owner_name,
        "organisme": site.organisme,
        "observation": site.observation,
        "has_gps": site.geom is not None,
        "contacts": contacts,
        "source": "DONNEE_ENREGISTREE",
    }


async def tool_missing_documents(db: AsyncSession, code: str) -> dict | None:
    site_result = await db.execute(select(Site).where(Site.code == code, Site.deleted_at.is_(None)))
    site = site_result.scalar_one_or_none()
    if site is None:
        return None

    missing = []
    if site.geom is None:
        missing.append("GPS")
    if not site.owner_name:
        missing.append("Propriétaire")

    contacts_count = (
        await db.execute(select(Contact).where(Contact.site_id == site.id, Contact.deleted_at.is_(None)))
    ).scalars().all()
    if not contacts_count:
        missing.append("Contact")

    doc_b = (await db.execute(select(DocB).where(DocB.site_id == site.id))).scalars().first()
    if doc_b is None:
        missing.append("Doc B")

    aps = (await db.execute(select(ApsDocument).where(ApsDocument.site_id == site.id))).scalars().first()
    if aps is None:
        missing.append("APS")

    contract = (
        await db.execute(select(Contract).where(Contract.site_id == site.id, Contract.deleted_at.is_(None)))
    ).scalars().first()
    if contract is None:
        missing.append("Contrat")

    return {"code": site.code, "missing": missing, "source": "DONNEE_ENREGISTREE"}


async def tool_contracts_expiring(db: AsyncSession, within_days: int = 60) -> list[dict]:
    limit_date = date.today() + timedelta(days=within_days)
    result = await db.execute(
        select(Contract.reference, Contract.date_expiration, Site.code)
        .join(Site, Contract.site_id == Site.id)
        .where(
            Contract.deleted_at.is_(None),
            Contract.date_expiration.is_not(None),
            Contract.date_expiration <= limit_date,
            Contract.date_expiration >= date.today(),
        )
    )
    return [
        {"reference": ref or "À COMPLÉTER", "date_expiration": exp.isoformat(), "site_code": code}
        for ref, exp, code in result.all()
    ]


async def tool_contact_role_lookup(db: AsyncSession, role: str, organisme: str | None) -> list[dict]:
    stmt = select(Contact, Site.code).join(Site, Contact.site_id == Site.id).where(
        Contact.role_label.ilike(f"%{role}%"), Contact.deleted_at.is_(None)
    )
    if organisme:
        stmt = stmt.where(Contact.organisme.ilike(f"%{organisme}%"))
    result = await db.execute(stmt)
    return [
        {
            "name": f"{c.first_name or ''} {c.last_name or ''}".strip() or "À COMPLÉTER",
            "site_code": code, "organisme": c.organisme, "phone": c.phone,
        }
        for c, code in result.all()
    ]


async def tool_list_documents_for_site(db: AsyncSession, code: str) -> list[dict]:
    site_result = await db.execute(select(Site).where(Site.code == code, Site.deleted_at.is_(None)))
    site = site_result.scalar_one_or_none()
    if site is None:
        return []
    result = await db.execute(
        select(Document.filename, Document.category, Document.version)
        .where(Document.site_id == site.id, Document.deleted_at.is_(None))
    )
    return [{"filename": f, "category": c, "version": v} for f, c, v in result.all()]
