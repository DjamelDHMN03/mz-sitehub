"""Routeur /users - liste legere des utilisateurs actifs (menus deroulants)."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserOption(BaseModel):
    id: uuid.UUID
    full_name: str


@router.get("/options", response_model=list[UserOption])
async def list_user_options(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOption]:
    """Utilisateurs actifs (id + nom) pour choisir un responsable / negociateur."""
    result = await db.execute(
        select(User)
        .where(User.is_active.is_(True), User.deleted_at.is_(None))
        .order_by(User.first_name, User.last_name)
    )
    return [UserOption(id=u.id, full_name=u.full_name) for u in result.scalars().all()]