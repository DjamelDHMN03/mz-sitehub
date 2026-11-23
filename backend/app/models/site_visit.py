"""
Modele ORM — TSS (Technical Site Survey) et CCT (Commission de Choix de Terrain)
planifiees dans le Calendrier. Une seule table, `visit_type` distingue les deux.
Les personnes presentes (BET, ingenieur radio, civil work, transmission,
negociateur) sont saisies en texte libre car souvent externes.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

VALID_VISIT_TYPES = {"TSS", "CCT"}


class SiteVisit(Base):
    __tablename__ = "site_visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_type: Mapped[str] = mapped_column(String, nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"))
    site_code: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    bet_name: Mapped[str | None] = mapped_column(String)
    radio_engineer_name: Mapped[str | None] = mapped_column(String)
    civil_work_name: Mapped[str | None] = mapped_column(String)
    transmission_name: Mapped[str | None] = mapped_column(String)
    negotiator_name: Mapped[str | None] = mapped_column(String)
    observation: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
