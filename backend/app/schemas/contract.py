import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

VALID_SIGNATORY_PARTIES = {"PROPRIETAIRE", "OOREDOO"}


class ContractBase(BaseModel):
    reference: str | None = None
    contract_type: str | None = None
    owner_party: str | None = None
    duration_years: float | None = None
    date_start: date | None = None
    date_end: date | None = None
    amount: float | None = Field(None, description="Montant — ne jamais estimer, laisser vide si inconnu")
    periodicity: str | None = None
    revision_clause: str | None = None
    conditions: str | None = None
    status: str | None = None
    date_sent: date | None = None
    date_signed: date | None = None
    date_expiration: date | None = None
    observation: str | None = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(ContractBase):
    pass


class ContractOut(ContractBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    site_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SignatoryBase(BaseModel):
    party: str = Field(..., description="PROPRIETAIRE ou OOREDOO")
    name: str | None = None
    role_label: str | None = None
    has_signing_power: bool | None = Field(
        None, description="Laisser vide (null) tant que le pouvoir de signature n'est pas vérifié"
    )
    proof_document_id: uuid.UUID | None = None


class SignatoryCreate(SignatoryBase):
    pass


class SignatoryUpdate(BaseModel):
    name: str | None = None
    role_label: str | None = None
    has_signing_power: bool | None = None
    proof_document_id: uuid.UUID | None = None


class SignatoryOut(SignatoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contract_id: uuid.UUID
