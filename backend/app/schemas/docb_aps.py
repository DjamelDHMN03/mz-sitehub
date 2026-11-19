import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# Types APS acceptés (section 38)
VALID_APS_TYPES = {
    "APS_V1", "APS_V2", "APS_V3", "PLAN_GC", "PLAN_STRUCTURE",
    "PLAN_TOITURE", "PLAN_PYLONE", "PLAN_RADIO", "TSS", "PHOTO_TECHNIQUE",
}


class DocBBase(BaseModel):
    date_preparation: date | None = None
    date_depot: date | None = None
    organisme: str | None = None
    reference: str | None = None
    status: str | None = None
    document_id: uuid.UUID | None = None
    version: int | None = None
    observation: str | None = None


class DocBCreate(DocBBase):
    pass


class DocBUpdate(DocBBase):
    pass


class DocBOut(DocBBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    site_id: uuid.UUID


class ApsBase(BaseModel):
    aps_type: str | None = None
    document_id: uuid.UUID | None = None
    version: int | None = None
    observation: str | None = None


class ApsCreate(ApsBase):
    aps_type: str = Field(..., description=f"Un de : {sorted(VALID_APS_TYPES)}")


class ApsUpdate(ApsBase):
    pass


class ApsOut(ApsBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    site_id: uuid.UUID
    created_at: datetime
