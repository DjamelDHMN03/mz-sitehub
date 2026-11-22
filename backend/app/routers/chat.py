"""Routeur /chat - discussion d'equipe (messages de groupe)."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    content: str
    created_at: datetime


def _to_out(message: ChatMessage, sender: User) -> ChatMessageOut:
    return ChatMessageOut(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=sender.full_name,
        content=message.content,
        created_at=message.created_at,
    )


@router.get("/messages", response_model=list[ChatMessageOut])
async def list_messages(
    after: datetime | None = None,
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageOut]:
    """Sans `after` : les derniers messages. Avec `after` : seulement les nouveaux."""
    stmt = select(ChatMessage, User).join(User, User.id == ChatMessage.sender_id)
    if after is not None:
        stmt = stmt.where(ChatMessage.created_at > after).order_by(ChatMessage.created_at.asc()).limit(limit)
        rows = (await db.execute(stmt)).all()
    else:
        stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)
        rows = list(reversed((await db.execute(stmt)).all()))
    return [_to_out(m, u) for m, u in rows]


@router.post("/messages", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def post_message(
    payload: ChatMessageIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageOut:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Le message est vide")
    message = ChatMessage(sender_id=current_user.id, content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return _to_out(message, current_user)