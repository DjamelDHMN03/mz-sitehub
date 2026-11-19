import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    site_id: uuid.UUID
    category: str
    filename: str
    mime_type: str | None
    size_bytes: int | None
    detected_code: str | None
    detected_type: str | None
    version: int
    created_at: datetime


class UploadAmbiguity(BaseModel):
    """Renvoyé (HTTP 422) quand la reconnaissance automatique du nom de
    fichier est ambiguë et que la catégorie n'a pas été fournie explicitement
    — section 41 : demander confirmation plutôt que deviner."""
    reason: str
    detected_code: str | None
    detected_category: str | None
    valid_categories: list[str]
