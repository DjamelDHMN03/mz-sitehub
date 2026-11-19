import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

VALID_INTERACTION_TYPES = {"APPEL", "WHATSAPP", "EMAIL", "REUNION", "VISITE", "COURRIER", "AUTRE"}


class ContactRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    label: str


class ContactBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    role_label: str | None = None
    organisme: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    last_contact_at: date | None = None
    next_followup_at: date | None = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    """Tous les champs optionnels — même principe de flexibilité totale que Site."""
    pass


class ContactOut(ContactBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    site_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class InteractionCreate(BaseModel):
    interaction_type: str = Field(..., description="APPEL, WHATSAPP, EMAIL, REUNION, VISITE, COURRIER, AUTRE")
    summary: str | None = None
    result: str | None = None
    next_action: str | None = None
    followup_at: date | None = None


class InteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contact_id: uuid.UUID
    site_id: uuid.UUID
    user_id: uuid.UUID | None
    interaction_type: str
    summary: str | None
    result: str | None
    next_action: str | None
    followup_at: date | None
    created_at: datetime
