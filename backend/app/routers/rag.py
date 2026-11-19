"""
Routeur RAG (sections 24, 64-65).

Flux d'indexation : Document (PDF) -> extract_pages -> chunk_pages ->
AIProvider.embed() pour chaque chunk -> stockage dans ai_document_chunks +
ai_embeddings.

Flux de recherche : question -> AIProvider.embed() -> recherche pgvector
(similarité cosinus) -> chunks les plus pertinents renvoyés AVEC leur
source (nom fichier, page) — jamais une réponse sans citation quand le RAG
est utilisé (section 65).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_ai_provider
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.ai_rag import AIDocumentChunk, AIEmbedding
from app.models.document import Document
from app.models.user import User
from app.services.rag import PdfExtractionError, chunk_pages, extract_pages
from app.services.storage import get_storage_provider

router = APIRouter(prefix="/rag", tags=["rag"])


class IndexResult(BaseModel):
    document_id: uuid.UUID
    chunks_created: int


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResultItem(BaseModel):
    content: str
    document_filename: str
    page_number: int | None
    score: float


@router.post("/documents/{document_id}/index", response_model=IndexResult)
async def index_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> IndexResult:
    document = await db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")
    if not document.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seuls les documents PDF sont indexables pour le RAG")

    storage = get_storage_provider()
    content = storage.read(document.storage_key)

    try:
        pages = extract_pages(content)
    except PdfExtractionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Aucun texte extractible dans ce PDF (scan non OCRisé ?) — impossible d'indexer",
        )

    provider = get_ai_provider()
    created = 0
    for chunk in chunks:
        embedding_vector = await provider.embed(chunk.content)

        db_chunk = AIDocumentChunk(
            document_id=document.id, chunk_index=chunk.chunk_index,
            content=chunk.content, page_number=chunk.page_number,
        )
        db.add(db_chunk)
        await db.flush()

        db.add(AIEmbedding(chunk_id=db_chunk.id, embedding=embedding_vector))
        created += 1

    await db.commit()
    return IndexResult(document_id=document.id, chunks_created=created)


@router.post("/search", response_model=list[SearchResultItem])
async def search_documents(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SearchResultItem]:
    provider = get_ai_provider()
    query_embedding = await provider.embed(payload.query)

    result = await db.execute(
        select(
            AIDocumentChunk.content,
            AIDocumentChunk.page_number,
            Document.filename,
            AIEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(AIEmbedding, AIEmbedding.chunk_id == AIDocumentChunk.id)
        .join(Document, Document.id == AIDocumentChunk.document_id)
        .where(Document.deleted_at.is_(None))
        .order_by("distance")
        .limit(payload.top_k)
    )

    return [
        SearchResultItem(
            content=content, document_filename=filename, page_number=page,
            score=1 - distance,
        )
        for content, page, filename, distance in result.all()
    ]
