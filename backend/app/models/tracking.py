"""
Modèles ORM — Contrats (minimal, complété en Phase 13), Doc B, APS
(complétés en Phase 12). Mappés sur database/migrations/001_init_core_schema.sql.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Contract(Base):
    """Contrats (section 35) — modèle complet, remplace le minimal de la
    Phase 6 (même table/classe, complétée sans rien casser)."""
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    reference: Mapped[str | None] = mapped_column(String)
    contract_type: Mapped[str | None] = mapped_column(String)
    owner_party: Mapped[str | None] = mapped_column(String)
    duration_years: Mapped[float | None] = mapped_column(Numeric)
    date_start: Mapped[date | None] = mapped_column(Date)
    date_end: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[float | None] = mapped_column(Numeric)
    periodicity: Mapped[str | None] = mapped_column(String)
    revision_clause: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String)
    date_sent: Mapped[date | None] = mapped_column(Date)
    date_signed: Mapped[date | None] = mapped_column(Date)
    date_expiration: Mapped[date | None] = mapped_column(Date)
    observation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContractSignatory(Base):
    """Signataires (section 36) : nom, fonction, pouvoir de signature,
    document justificatif (lié à la GED de la Phase 11)."""
    __tablename__ = "contract_signatories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    party: Mapped[str] = mapped_column(String, nullable=False)  # 'PROPRIETAIRE' ou 'OOREDOO'
    name: Mapped[str | None] = mapped_column(String)
    role_label: Mapped[str | None] = mapped_column(String)
    has_signing_power: Mapped[bool | None] = mapped_column(Boolean)
    proof_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))


class DocB(Base):
    """Doc B (section 37) — pas de `deleted_at` : la table n'a pas cette
    colonne dans la migration 001 (contrairement à sites/contacts/documents).
    Une entrée Doc B est un enregistrement administratif léger pointant vers
    un Document déjà versionné ; sa suppression est une vraie suppression."""
    __tablename__ = "doc_b"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    date_preparation: Mapped[date | None] = mapped_column(Date)
    date_depot: Mapped[date | None] = mapped_column(Date)
    organisme: Mapped[str | None] = mapped_column(String)
    reference: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    observation: Mapped[str | None] = mapped_column(Text)


class ApsDocument(Base):
    """APS / Plans (section 38) — mêmes remarques que DocB (pas de soft delete)."""
    __tablename__ = "aps_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    aps_type: Mapped[str | None] = mapped_column(String)  # APS_V1, PLAN_GC, TSS, PHOTO_TECHNIQUE...
    version: Mapped[int] = mapped_column(Integer, default=1)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    observation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
