"""
Modèles ORM — RAG (ai_document_chunks, ai_embeddings). Mappés sur la
migration 001. La dimension du vecteur (768) correspond au modèle
d'embedding local par défaut (nomic-embed-text) — à ajuster si un autre
modèle d'embedding est configuré (voir .env OLLAMA_EMBED_MODEL).
"""
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

EMBEDDING_DIMENSIONS = 768


class AIDocumentChunk(Base):
    __tablename__ = "ai_document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)


class AIEmbedding(Base):
    __tablename__ = "ai_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_document_chunks.id"), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
