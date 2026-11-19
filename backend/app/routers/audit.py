"""
Routeur Historique / Audit (section 19 : consultation de ce qui est déjà
tracé automatiquement par `log_audit` depuis la Phase 4, dans tous les
modules construits depuis). Lecture seule — l'audit ne doit jamais être
modifiable depuis l'application.
"""
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut, AuditLogPage

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=AuditLogPage)
async def list_audit_logs(
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    since: date | None = None,
    until: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogPage:
    stmt = select(AuditLog, User.email).outerjoin(User, AuditLog.user_id == User.id)
    count_stmt = select(func.count()).select_from(AuditLog)

    filters = []
    if entity:
        filters.append(AuditLog.entity == entity)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action == action)
    if since:
        filters.append(AuditLog.occurred_at >= datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc))
    if until:
        filters.append(AuditLog.occurred_at <= datetime.combine(until, datetime.max.time(), tzinfo=timezone.utc))

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(AuditLog.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)

    items = [
        AuditLogOut(
            id=log.id, user_email=email, entity=log.entity, entity_id=log.entity_id,
            action=log.action, field=log.field, old_value=log.old_value,
            new_value=log.new_value, occurred_at=log.occurred_at,
        )
        for log, email in result.all()
    ]

    return AuditLogPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/entities", response_model=list[str])
async def list_audited_entities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Liste des types d'entités réellement présents dans l'audit — pour
    peupler le filtre du frontend sans figer une liste en dur qui pourrait
    diverger des entités réellement tracées."""
    result = await db.execute(select(AuditLog.entity).distinct().order_by(AuditLog.entity))
    return [row[0] for row in result.all()]
