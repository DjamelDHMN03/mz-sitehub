"""
Routeur Tasks / Actions (section 54). Sert aussi de source de données pour
le Calendrier (section 55, filtre par plage de dates) — pas de duplication
de logique, le frontend interroge cette même API avec des filtres différents.
"""
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.task import VALID_TASK_STATUSES, Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskListResponse, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    if payload.status and payload.status not in VALID_TASK_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Statut invalide : {sorted(VALID_TASK_STATUSES)}")

    now = datetime.now(timezone.utc)
    task = Task(
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
        priority=payload.priority or 2,
        status=payload.status or "A_FAIRE",
        **payload.model_dump(exclude={"priority", "status"}),
    )
    db.add(task)
    await db.flush()

    await log_audit(db, user_id=current_user.id, entity="tasks", entity_id=task.id, action="CREATE", new_value=task.title)
    await db.commit()
    await db.refresh(task)
    return TaskOut.model_validate(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    site_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    responsible_user_id: uuid.UUID | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    stmt = select(Task)
    count_stmt = select(func.count()).select_from(Task)

    filters = []
    if site_id:
        filters.append(Task.site_id == site_id)
    if status_filter:
        filters.append(Task.status == status_filter)
    if responsible_user_id:
        filters.append(Task.responsible_user_id == responsible_user_id)
    if due_before:
        filters.append(Task.due_date <= due_before)
    if due_after:
        filters.append(Task.due_date >= due_after)

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        stmt.order_by(Task.due_date.asc().nulls_last())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)

    return TaskListResponse(
        items=[TaskOut.model_validate(t) for t in result.scalars().all()],
        total=total, page=page, page_size=page_size,
    )


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tâche introuvable")

    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in VALID_TASK_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Statut invalide : {sorted(VALID_TASK_STATUSES)}")

    for field, new_value in changes.items():
        old_value = getattr(task, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="tasks", entity_id=task.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(task, field, new_value)

    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tâche introuvable")
    await log_audit(db, user_id=current_user.id, entity="tasks", entity_id=task.id, action="DELETE")
    await db.delete(task)
    await db.commit()
