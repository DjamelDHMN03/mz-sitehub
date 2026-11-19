"""
Modèle ORM — Tâches / Actions (section 54). `site_id` est optionnel : une
tâche peut être générale (pas liée à un site précis), comme dans la
migration 001 (`site_id UUID REFERENCES sites(id)`, sans NOT NULL).
"""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, SmallInteger, String, Text, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

VALID_TASK_STATUSES = {"A_FAIRE", "EN_COURS", "TERMINE", "ANNULE"}


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    priority: Mapped[int] = mapped_column(SmallInteger, default=2)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, default="A_FAIRE")
    comment: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
