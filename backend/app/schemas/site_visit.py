"""Schemas Pydantic — TSS / CCT du calendrier."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SiteVisitCreate(BaseModel):
    visit_type: str = Field(..., max_length=10)  # "TSS" ou "CCT"
    visit_date: date
    site_code: str = Field(..., min_length=1, max_length=64)
    location: str | None = Field(None, max_length=300)
    bet_name: str | None = Field(None, max_length=200)
    radio_engineer_name: str | None = Field(None, max_length=200)
    civil_work_name: str | None = Field(None, max_length=200)
    transmission_name: str | None = Field(None, max_length=200)
    negotiator_name: str | None = Field(None, max_length=200)
    observation: str | None = Field(None, max_length=2000)


class SiteVisitUpdate(BaseModel):
    visit_type: str | None = Field(None, max_length=10)
    visit_date: date | None = None
    site_code: str | None = Field(None, min_length=1, max_length=64)
    location: str | None = Field(None, max_length=300)
    bet_name: str | None = Field(None, max_length=200)
    radio_engineer_name: str | None = Field(None, max_length=200)
    civil_work_name: str | None = Field(None, max_length=200)
    transmission_name: str | None = Field(None, max_length=200)
    negotiator_name: str | None = Field(None, max_length=200)
    observation: str | None = Field(None, max_length=2000)


class SiteVisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_type: str
    visit_date: date
    site_id: uuid.UUID | None
    site_code: str
    location: str | None
    bet_name: str | None
    radio_engineer_name: str | None
    civil_work_name: str | None
    transmission_name: str | None
    negotiator_name: str | None
    observation: str | None
    created_at: datetime
    updated_at: datetime


class SiteOption(BaseModel):
    code: str
    responsible_name: str | None
