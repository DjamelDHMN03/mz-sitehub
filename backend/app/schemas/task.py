import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    site_id: uuid.UUID | None = None
    title: str | None = None
    responsible_user_id: uuid.UUID | None = None
    priority: int | None = Field(None, ge=1, le=3)
    due_date: date | None = None
    status: str | None = None
    comment: str | None = None


class TaskCreate(TaskBase):
    title: str = Field(..., min_length=1)


class TaskUpdate(TaskBase):
    pass


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    site_id: uuid.UUID | None
    title: str
    responsible_user_id: uuid.UUID | None
    priority: int
    due_date: date | None
    status: str
    comment: str | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Pagination ajoutée en Phase 23 (section 84) — /tasks n'avait aucune
    limite, un vrai risque à l'échelle de 10 000 sites."""
    items: list[TaskOut]
    total: int
    page: int
    page_size: int
