import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MapLayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    original_filename: str | None
    is_visible: bool
    feature_count: int
    created_at: datetime


class MapFeatureOut(BaseModel):
    id: uuid.UUID
    name: str | None
    geometry_type: str
    detected_code: str | None
    has_geometry: bool  # False si non convertible (ex. MultiGeometry hétérogène)


class ImportResult(BaseModel):
    layer: MapLayerOut
    features: list[MapFeatureOut]
    features_without_geometry: int


class LinkSuggestion(BaseModel):
    """Pour chaque feature détectée avec un code, indique si un site existe déjà
    (section 29 : proposer le rattachement, ou signaler un nouveau site)."""
    feature_id: uuid.UUID
    detected_code: str
    existing_site_id: uuid.UUID | None
    suggestion: str  # "RATTACHER" ou "NOUVEAU_SITE"


class LinkFeatureRequest(BaseModel):
    action: str  # "CREER" | "IGNORER" | "RATTACHER"
    site_id: uuid.UUID | None = None  # requis si action == "RATTACHER"
