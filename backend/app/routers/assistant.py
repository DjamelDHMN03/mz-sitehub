"""
Routeur MZ ASSISTANT (sections 61, 69-71).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assistant import answer_question
from app.ai.intent import INTENT_ADD_CONTACT, INTENT_UNKNOWN, parse_intent
from app.ai.llm_assistant import AssistantUnavailable, HistoryItem, ask_business_assistant
from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.ai_conversation import AIConversation, AIMessage
from app.models.contact import Contact
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None
    history: list[HistoryItem] = []


class PendingAction(BaseModel):
    action: str
    params: dict


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    data: dict | list | None = None
    pending_action: PendingAction | None = None


class ConfirmActionRequest(BaseModel):
    action: str
    params: dict


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    now = datetime.now(timezone.utc)

    if payload.conversation_id:
        conversation = await db.get(AIConversation, payload.conversation_id)
        if conversation is None or conversation.user_id != current_user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")
    else:
        conversation = AIConversation(user_id=current_user.id, title=payload.message[:80], created_at=now)
        db.add(conversation)
        await db.flush()

    db.add(AIMessage(conversation_id=conversation.id, role="user", content=payload.message, created_at=now))

    # Section 69 : une action détectée n'est JAMAIS exécutée directement ici —
    # elle est renvoyée au frontend pour confirmation explicite (bouton CONFIRMER).
    intent = parse_intent(payload.message)
    if intent.type == INTENT_ADD_CONTACT:
        answer_text = (
            f"Je vais ajouter {intent.params['name']} comme {intent.params['role']} "
            f"sur le site {intent.params['code']}. Confirmez-vous ?"
        )
        db.add(AIMessage(conversation_id=conversation.id, role="assistant", content=answer_text, created_at=now))
        await db.commit()
        return ChatResponse(
            conversation_id=conversation.id,
            answer=answer_text,
            pending_action=PendingAction(action=INTENT_ADD_CONTACT, params=intent.params),
        )

    result = await answer_question(db, payload.message)
    if result.intent_type == INTENT_UNKNOWN:
        try:
            llm_text = await ask_business_assistant(db, current_user, payload.message, payload.history)
        except AssistantUnavailable:
            llm_text = (
                "L'assistant IA est momentan\u00e9ment indisponible. Les commandes habituelles "
                "restent disponibles : \"sites bloqu\u00e9s\", \"r\u00e9sume AL6328\", \"contrats qui expirent bient\u00f4t\"."
            )
        if llm_text:
            result.text = llm_text
    db.add(AIMessage(conversation_id=conversation.id, role="assistant", content=result.text, created_at=now))
    await db.commit()

    return ChatResponse(conversation_id=conversation.id, answer=result.text, data=result.data)


@router.post("/confirm-action")
async def confirm_action(
    payload: ConfirmActionRequest,
    current_user: User = Depends(require_permission("contacts", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Exécute réellement une action seulement après confirmation explicite
    de l'utilisateur (section 69 : "Aucune modification de données sans
    confirmation explicite")."""
    if payload.action != INTENT_ADD_CONTACT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Action non supportée : {payload.action}")

    code = payload.params.get("code")
    name = payload.params.get("name", "")
    role = payload.params.get("role")

    site_result = await db.execute(select(Site).where(Site.code == code, Site.deleted_at.is_(None)))
    site = site_result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Site {code} introuvable")

    parts = name.split(maxsplit=1)
    first_name, last_name = (parts[0], parts[1]) if len(parts) > 1 else (name, None)

    now = datetime.now(timezone.utc)
    contact = Contact(
        site_id=site.id, first_name=first_name, last_name=last_name, role_label=role,
        created_at=now, updated_at=now,
    )
    db.add(contact)
    await db.flush()

    await log_audit(
        db, user_id=current_user.id, entity="contacts", entity_id=contact.id,
        action="CREATE_VIA_ASSISTANT", new_value=f"{name} ({role}) sur {code}",
    )
    await db.commit()

    return {"status": "confirmé", "contact_id": str(contact.id)}


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    owner_id = (
        await db.execute(select(AIConversation.user_id).where(AIConversation.id == conversation_id))
    ).scalar_one_or_none()
    if owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")
    result = await db.execute(
        select(AIMessage).where(AIMessage.conversation_id == conversation_id).order_by(AIMessage.created_at)
    )
    return [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in result.scalars().all()]


@router.get("/briefing")
async def get_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Section 71 : BRIEFING ACQUISITION — réutilise les mêmes tools que le
    chat, pas de nouvelle logique de requête dupliquée."""
    from app.ai import tools as ai_tools

    bloques = await ai_tools.tool_list_sites_by_status(db, "BLOQUE")
    negociation = await ai_tools.tool_list_sites_by_status(db, "NEGOCIATION")
    contrats_expirant = await ai_tools.tool_contracts_expiring(db, within_days=60)

    return {
        "sites_bloques": bloques,
        "sites_negociation": negociation,
        "contrats_a_expirer": contrats_expirant,
    }
