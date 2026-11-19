import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    user_email: str | None
    entity: str
    entity_id: uuid.UUID | None
    action: str
    field: str | None
    old_value: str | None
    new_value: str | None
    occurred_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
