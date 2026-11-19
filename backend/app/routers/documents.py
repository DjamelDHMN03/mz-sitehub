"""
Routeur Documents / GED (sections 39-43).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.core.upload_limits import MAX_UPLOAD_SIZE_BYTES, assert_upload_size_ok
from app.db.session import get_db
from app.models.document import VALID_CATEGORIES, Document, DocumentVersion
from app.models.site import Site
from app.models.user import User
from app.schemas.document import DocumentOut
from app.services.document_recognition import recognize_filename
from app.services.storage import get_storage_provider, make_relative_path

router = APIRouter(tags=["documents"])

# MAX_UPLOAD_SIZE_BYTES importé depuis app.core.upload_limits (section 82) —
# centralisé après l'audit Phase 21 (map_layers/excel_import n'avaient aucune limite).


async def _get_site_or_404(db: AsyncSession, site_id: uuid.UUID) -> Site:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.deleted_at.is_(None)))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")
    return site


async def _get_document_or_404(db: AsyncSession, document_id: uuid.UUID) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")
    return doc


@router.post("/sites/{site_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    site_id: uuid.UUID,
    file: UploadFile,
    category: str | None = Query(
        None, description="Catégorie explicite ; si omise, détection automatique depuis le nom de fichier"
    ),
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    site = await _get_site_or_404(db, site_id)
    filename = file.filename or "sans_nom"

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Fichier trop volumineux (max {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} Mo)",
        )

    recognition = recognize_filename(filename)
    final_category = category or recognition.detected_category

    if final_category is None:
        # Section 41 : ambigu -> on ne devine pas, on demande une catégorie explicite.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "reason": recognition.ambiguity_reason,
                "detected_code": recognition.detected_code,
                "detected_category": recognition.detected_category,
                "valid_categories": sorted(VALID_CATEGORIES),
            },
        )

    if final_category not in VALID_CATEGORIES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Catégorie invalide : {final_category}. Valeurs acceptées : {sorted(VALID_CATEGORIES)}",
        )

    storage = get_storage_provider()
    relative_path = make_relative_path(site.code, final_category, filename)
    storage_key = storage.save(content, relative_path)

    now = datetime.now(timezone.utc)
    document = Document(
        site_id=site_id,
        category=final_category,
        filename=filename,
        storage_key=storage_key,
        mime_type=file.content_type,
        size_bytes=len(content),
        detected_code=recognition.detected_code,
        detected_type=recognition.detected_category,
        version=recognition.detected_version or 1,
        uploaded_by=current_user.id,
        created_at=now,
    )
    db.add(document)
    await db.flush()

    await log_audit(
        db, user_id=current_user.id, entity="documents", entity_id=document.id,
        action="UPLOAD", new_value=filename,
    )
    await db.commit()
    await db.refresh(document)
    return DocumentOut.model_validate(document)


@router.get("/sites/{site_id}/documents", response_model=list[DocumentOut])
async def list_site_documents(
    site_id: uuid.UUID,
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    stmt = select(Document).where(Document.site_id == site_id, Document.deleted_at.is_(None))
    if category:
        stmt = stmt.where(Document.category == category)
    result = await db.execute(stmt.order_by(Document.created_at.desc()))
    return [DocumentOut.model_validate(d) for d in result.scalars().all()]


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Le fichier ne passe jamais par une URL de stockage directe — toujours
    via cette route authentifiée (section 51 : ne jamais contourner les
    permissions en récupérant l'URL de stockage brute)."""
    document = await _get_document_or_404(db, document_id)
    storage = get_storage_provider()

    if not storage.exists(document.storage_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier introuvable sur le stockage")

    content = storage.read(document.storage_key)
    return Response(
        content=content,
        media_type=document.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )


@router.post(
    "/documents/{document_id}/new-version",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_new_version(
    document_id: uuid.UUID,
    file: UploadFile,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """Ne jamais écraser silencieusement (section 42) : l'ancienne version est
    conservée dans document_versions avant que le document ne pointe vers la nouvelle."""
    document = await _get_document_or_404(db, document_id)
    site = await _get_site_or_404(db, document.site_id)

    # Archive la version actuelle avant de la remplacer
    old_version = DocumentVersion(
        document_id=document.id,
        version=document.version,
        storage_key=document.storage_key,
        uploaded_by=document.uploaded_by,
        created_at=document.created_at,
    )
    db.add(old_version)

    content = await file.read()
    filename = file.filename or document.filename
    storage = get_storage_provider()
    relative_path = make_relative_path(site.code, document.category, filename)
    storage_key = storage.save(content, relative_path)

    document.storage_key = storage_key
    document.filename = filename
    document.mime_type = file.content_type
    document.size_bytes = len(content)
    document.version += 1
    document.uploaded_by = current_user.id
    document.created_at = datetime.now(timezone.utc)  # date de la dernière version

    await log_audit(
        db, user_id=current_user.id, entity="documents", entity_id=document.id,
        action="NEW_VERSION", field="version", new_value=str(document.version),
    )
    await db.commit()
    await db.refresh(document)
    return DocumentOut.model_validate(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete uniquement — le fichier physique n'est jamais supprimé ici
    (section 18 : corbeille avant toute suppression définitive)."""
    document = await _get_document_or_404(db, document_id)
    document.deleted_at = datetime.now(timezone.utc)
    await log_audit(db, user_id=current_user.id, entity="documents", entity_id=document.id, action="DELETE")
    await db.commit()
