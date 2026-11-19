"""
Routeur Partage documentaire (sections 44-51).

Principes :
- Le fichier n'est jamais exposé via une URL de storage directe (section 51) :
  seul le token opaque circule, et /shares/{token}/download revérifie la
  validité (expiration/révocation) à chaque accès.
- Outlook/WhatsApp/Telegram : on ne fait qu'ouvrir une fenêtre de composition
  pré-remplie (deep link) — jamais d'envoi automatique (section 44/45/46).
"""
import urllib.parse
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.config import get_settings
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.document import Document
from app.models.share import VALID_PLATFORMS, DocumentShareHistory, DocumentShareLink, DocumentShareRecipient
from app.models.site import Site
from app.models.user import User
from app.schemas.share import ShareCreateRequest, ShareFolderRequest, ShareInfoOut, ShareLinkOut
from app.services.share import build_zip_archive, compute_expiry, generate_share_token, is_link_valid
from app.services.storage import get_storage_provider

router = APIRouter(tags=["sharing"])
settings = get_settings()


def _build_platform_urls(share_url: str, site_code: str | None) -> dict[str, str]:
    """Deep links prêts à l'emploi — l'utilisateur reste maître de l'envoi."""
    message = f"Documents{f' — site {site_code}' if site_code else ''} : {share_url}"
    encoded_message = urllib.parse.quote(message)
    return {
        "whatsapp_url": f"https://wa.me/?text={encoded_message}",
        "telegram_url": f"https://t.me/share/url?url={urllib.parse.quote(share_url)}&text={urllib.parse.quote(message)}",
        "outlook_compose_url": (
            "https://outlook.office.com/mail/deeplink/compose?"
            f"subject={urllib.parse.quote('Documents MZ BUILDING')}&body={encoded_message}"
        ),
    }


async def _create_share(
    db: AsyncSession,
    current_user: User,
    document_ids: list[uuid.UUID],
    site_id: uuid.UUID | None,
    platform: str | None,
    expiry_preset: str | None,
    custom_expiry: datetime | None,
    recipients: list[str],
) -> DocumentShareLink:
    if platform is not None and platform not in VALID_PLATFORMS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Plateforme invalide : {sorted(VALID_PLATFORMS)}")

    try:
        expires_at = compute_expiry(expiry_preset, custom=custom_expiry)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    link = DocumentShareLink(
        token=generate_share_token(),
        created_by=current_user.id,
        site_id=site_id,
        document_ids=document_ids,
        platform=platform,
        expires_at=expires_at,
        is_revoked=False,
        download_count=0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(link)
    await db.flush()

    for recipient in recipients:
        db.add(DocumentShareRecipient(share_link_id=link.id, recipient=recipient))

    await log_audit(
        db, user_id=current_user.id, entity="document_share_links", entity_id=link.id,
        action="CREATE", new_value=f"{len(document_ids)} document(s)",
    )
    await db.commit()
    await db.refresh(link)
    return link


def _to_share_link_out(link: DocumentShareLink, site_code: str | None) -> ShareLinkOut:
    share_url = f"{settings.share_link_base_url}/{link.token}"
    urls = _build_platform_urls(share_url, site_code)
    return ShareLinkOut(
        id=link.id,
        token=link.token,
        share_url=share_url,
        document_ids=link.document_ids,
        platform=link.platform,
        expires_at=link.expires_at,
        is_revoked=link.is_revoked,
        download_count=link.download_count,
        created_at=link.created_at,
        **urls,
    )


@router.post("/shares", response_model=ShareLinkOut, status_code=status.HTTP_201_CREATED)
async def create_share(
    payload: ShareCreateRequest,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkOut:
    # Vérifie que les documents existent et récupère le site pour le message
    result = await db.execute(
        select(Document).where(Document.id.in_(payload.document_ids), Document.deleted_at.is_(None))
    )
    documents = result.scalars().all()
    if len(documents) != len(payload.document_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Un ou plusieurs documents sont introuvables")

    site_id = documents[0].site_id if documents else None
    site = await db.get(Site, site_id) if site_id else None

    link = await _create_share(
        db, current_user, payload.document_ids, site_id,
        payload.platform, payload.expiry_preset, payload.custom_expiry, payload.recipients,
    )
    return _to_share_link_out(link, site.code if site else None)


@router.post("/sites/{site_id}/share-folder", response_model=ShareLinkOut, status_code=status.HTTP_201_CREATED)
async def share_folder(
    site_id: uuid.UUID,
    payload: ShareFolderRequest,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkOut:
    """Section 50 : PARTAGER LE DOSSIER — sélection de catégories entières."""
    site = await db.get(Site, site_id)
    if site is None or site.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")

    result = await db.execute(
        select(Document).where(
            Document.site_id == site_id,
            Document.category.in_(payload.categories),
            Document.deleted_at.is_(None),
        )
    )
    documents = result.scalars().all()
    if not documents:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Aucun document trouvé pour les catégories sélectionnées sur ce site",
        )

    link = await _create_share(
        db, current_user, [d.id for d in documents], site_id,
        payload.platform, payload.expiry_preset, payload.custom_expiry, payload.recipients,
    )
    return _to_share_link_out(link, site.code)


@router.get("/sites/{site_id}/shares", response_model=list[ShareLinkOut])
async def list_site_shares(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ShareLinkOut]:
    """Historique de partage pour un site (section 48)."""
    site = await db.get(Site, site_id)
    result = await db.execute(
        select(DocumentShareLink)
        .where(DocumentShareLink.site_id == site_id)
        .order_by(DocumentShareLink.created_at.desc())
    )
    return [_to_share_link_out(link, site.code if site else None) for link in result.scalars().all()]


@router.post("/shares/{link_id}/revoke", response_model=ShareLinkOut)
async def revoke_share(
    link_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkOut:
    link = await db.get(DocumentShareLink, link_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lien introuvable")
    link.is_revoked = True
    await log_audit(db, user_id=current_user.id, entity="document_share_links", entity_id=link.id, action="REVOKE")
    await db.commit()
    await db.refresh(link)
    site = await db.get(Site, link.site_id) if link.site_id else None
    return _to_share_link_out(link, site.code if site else None)


# ------------------------------------------------------------------
# Endpoints PUBLICS (sans authentification) — consultés par le destinataire
# du lien, qui n'a pas de compte MZ SITEHUB.
# ------------------------------------------------------------------
@router.get("/shares/{token}/info", response_model=ShareInfoOut)
async def get_share_info(token: str, db: AsyncSession = Depends(get_db)) -> ShareInfoOut:
    result = await db.execute(select(DocumentShareLink).where(DocumentShareLink.token == token))
    link = result.scalar_one_or_none()
    if link is None:
        return ShareInfoOut(is_valid=False, reason="Lien introuvable", filenames=[], site_code=None)

    valid, reason = is_link_valid(link.expires_at, link.is_revoked)
    site = await db.get(Site, link.site_id) if link.site_id else None

    filenames: list[str] = []
    if valid:
        doc_result = await db.execute(select(Document).where(Document.id.in_(link.document_ids)))
        filenames = [d.filename for d in doc_result.scalars().all()]

    return ShareInfoOut(is_valid=valid, reason=reason, filenames=filenames, site_code=site.code if site else None)


@router.get("/shares/{token}/download")
async def download_shared(token: str, request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(select(DocumentShareLink).where(DocumentShareLink.token == token))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lien introuvable")

    valid, reason = is_link_valid(link.expires_at, link.is_revoked)
    if not valid:
        raise HTTPException(status.HTTP_410_GONE, reason)

    doc_result = await db.execute(select(Document).where(Document.id.in_(link.document_ids)))
    documents = doc_result.scalars().all()
    if not documents:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documents introuvables (peut-être supprimés depuis)")

    storage = get_storage_provider()

    link.download_count += 1
    db.add(DocumentShareHistory(
        share_link_id=link.id,
        accessed_at=datetime.now(timezone.utc),
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    if len(documents) == 1:
        doc = documents[0]
        content = storage.read(doc.storage_key)
        return Response(
            content=content,
            media_type=doc.mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
        )

    # Partage multiple -> ZIP (section 49)
    files = [(d.filename, storage.read(d.storage_key)) for d in documents]
    zip_bytes = build_zip_archive(files)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="documents_mz_building.zip"'},
    )
