"""
Modèles ORM — Référentiel géographique, statuts, et Sites.
Mappés sur database/migrations/001_init_core_schema.sql (source de vérité).
"""
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    DateTime,
    JSON,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Wilaya(Base):
    __tablename__ = "wilayas"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class Commune(Base):
    __tablename__ = "communes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wilaya_id: Mapped[int] = mapped_column(ForeignKey("wilayas.id"), nullable=False)
    daira: Mapped[str | None] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False)


class SiteStatus(Base):
    __tablename__ = "site_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    previous_codes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    name: Mapped[str | None] = mapped_column(String)
    wilaya_id: Mapped[int | None] = mapped_column(ForeignKey("wilayas.id"))
    commune_id: Mapped[int | None] = mapped_column(ForeignKey("communes.id"))
    address: Mapped[str | None] = mapped_column(Text)

    # GPS : NULL si inconnu — ne jamais inventer (section 74)
    geom: Mapped[str | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)

    site_type: Mapped[str | None] = mapped_column(String)
    owner_name: Mapped[str | None] = mapped_column(String)
    organisme: Mapped[str | None] = mapped_column(String)
    status_id: Mapped[int] = mapped_column(ForeignKey("site_status.id"), nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, default=2)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    secondary_responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    next_action: Mapped[str | None] = mapped_column(Text)
    observation: Mapped[str | None] = mapped_column(Text)
    is_favorite: Mapped[bool] = mapped_column(default=False)
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped["SiteStatus"] = relationship()


class SiteHistory(Base):
    __tablename__ = "site_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"))
    field: Mapped[str] = mapped_column(String, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
