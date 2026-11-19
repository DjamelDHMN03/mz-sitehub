"""
Schémas Pydantic — Sites.

Section 16 du cahier des charges : TOUTES les informations doivent être
modifiables. SiteUpdate expose donc tous les champs en optionnel (PATCH
partiel) plutôt qu'un schéma figé par cas d'usage.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SiteBase(BaseModel):
    name: str | None = None
    wilaya_id: int | None = None
    commune_id: int | None = None
    address: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    site_type: str | None = None
    owner_name: str | None = None
    organisme: str | None = None
    status_id: int | None = None
    priority: int | None = Field(None, ge=1, le=3)
    responsible_user_id: uuid.UUID | None = None
    secondary_responsible_user_id: uuid.UUID | None = None
    next_action: str | None = None
    observation: str | None = None
    is_favorite: bool | None = None
    custom_fields: dict | None = None


class SiteCreate(SiteBase):
    code: str = Field(..., min_length=2, max_length=32)
    status_id: int  # obligatoire à la création


class SiteUpdate(SiteBase):
    """Tous les champs optionnels — PATCH partiel, y compris le code (section 17)."""
    code: str | None = Field(None, min_length=2, max_length=32)


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    previous_codes: list[str]
    name: str | None
    wilaya_id: int | None
    commune_id: int | None
    address: str | None
    latitude: float | None
    longitude: float | None
    site_type: str | None
    owner_name: str | None
    organisme: str | None
    status_id: int
    priority: int
    responsible_user_id: uuid.UUID | None
    secondary_responsible_user_id: uuid.UUID | None
    next_action: str | None
    observation: str | None
    is_favorite: bool
    custom_fields: dict
    created_at: datetime
    updated_at: datetime


class SiteListItem(BaseModel):
    """Version allégée pour les listes (carte + tableau) — évite de charger
    observation/custom_fields sur 10 000 lignes (section 84 performance)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str | None
    wilaya_id: int | None
    status_id: int
    priority: int
    latitude: float | None
    longitude: float | None
    is_favorite: bool


class SiteListResponse(BaseModel):
    items: list[SiteListItem]
    total: int
    page: int
    page_size: int


class CodeChangeConfirm(BaseModel):
    new_code: str = Field(..., min_length=2, max_length=32)
    confirm: bool = False
