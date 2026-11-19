"""
Modèles ORM — Couches cartographiques importées (KMZ/KML/GeoJSON).
Mappés sur database/migrations/001_init_core_schema.sql.
"""
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, ForeignKey, Integer, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class MapLayer(Base):
    __tablename__ = "map_layers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # KML, KMZ, GEOJSON
    original_filename: Mapped[str | None] = mapped_column(String)
    storage_key: Mapped[str | None] = mapped_column(String)  # fichier original téléchargeable
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MapFeature(Base):
    __tablename__ = "map_features"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("map_layers.id"))
    name: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    geometry_type: Mapped[str] = mapped_column(String, nullable=False)
    geom: Mapped[str | None] = mapped_column(Geometry("GEOMETRY", srid=4326))
    style: Mapped[dict | None] = mapped_column(JSON)
    detected_code: Mapped[str | None] = mapped_column(String)
    raw_attributes: Mapped[dict | None] = mapped_column(JSON)


class MapFeatureSite(Base):
    __tablename__ = "map_feature_sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    map_feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("map_features.id"))
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"))
    linked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
