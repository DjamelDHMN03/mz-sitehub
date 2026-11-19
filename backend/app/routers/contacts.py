"""
Routeur Contacts / CRM (sections 32-34).

Chaque nouvelle interaction met à jour automatiquement `last_contact_at` et
`next_followup_at` sur le contact — évite d'avoir à saisir deux fois la même
information (une fois dans l'historique, une fois sur la fiche contact).
"""
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.contact import Contact, ContactInteraction, ContactRole
from app.models.site import Site
from app.models.user import User
from app.schemas.contact import (
    VALID_INTERACTION_TYPES,
    ContactCreate,
    ContactOut,
    ContactRoleOut,
    ContactUpdate,
    InteractionCreate,
    InteractionOut,
)

router = APIRouter(tags=["contacts"])


@router.get("/contact-roles", response_model=list[ContactRoleOut])
async def list_contact_roles(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContactRoleOut]:
    response.headers["Cache-Control"] = "private, max-age=300"  # référentiel figé, quasi jamais modifié
    result = await db.execute(select(ContactRole).order_by(ContactRole.label))
    return [ContactRoleOut.model_validate(r) for r in result.scalars().all()]


async def _get_site_or_404(db: AsyncSession, site_id: uuid.UUID) -> Site:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.deleted_at.is_(None)))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site introuvable")
    return site


async def _get_contact_or_404(db: AsyncSession, contact_id: uuid.UUID) -> Contact:
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.deleted_at.is_(None))
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact introuvable")
    return contact


@router.post("/sites/{site_id}/contacts", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(
    site_id: uuid.UUID,
    payload: ContactCreate,
    current_user: User = Depends(require_permission("contacts", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    await _get_site_or_404(db, site_id)

    now = datetime.now(timezone.utc)
    contact = Contact(site_id=site_id, created_at=now, updated_at=now, **payload.model_dump())
    db.add(contact)
    await db.flush()

    await log_audit(
        db, user_id=current_user.id, entity="contacts", entity_id=contact.id,
        action="CREATE", new_value=f"{contact.first_name} {contact.last_name}".strip(),
    )
    await db.commit()
    await db.refresh(contact)
    return ContactOut.model_validate(contact)


@router.get("/sites/{site_id}/contacts", response_model=list[ContactOut])
async def list_site_contacts(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContactOut]:
    result = await db.execute(
        select(Contact)
        .where(Contact.site_id == site_id, Contact.deleted_at.is_(None))
        .order_by(Contact.created_at.desc())
    )
    return [ContactOut.model_validate(c) for c in result.scalars().all()]


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    current_user: User = Depends(require_permission("contacts", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    contact = await _get_contact_or_404(db, contact_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, new_value in changes.items():
        old_value = getattr(contact, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="contacts", entity_id=contact.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(contact, field, new_value)

    contact.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(contact)
    return ContactOut.model_validate(contact)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(require_permission("contacts", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> None:
    contact = await _get_contact_or_404(db, contact_id)
    contact.deleted_at = datetime.now(timezone.utc)
    await log_audit(db, user_id=current_user.id, entity="contacts", entity_id=contact.id, action="DELETE")
    await db.commit()


@router.post(
    "/contacts/{contact_id}/interactions",
    response_model=InteractionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_interaction(
    contact_id: uuid.UUID,
    payload: InteractionCreate,
    current_user: User = Depends(require_permission("contacts", "write_own")),
    db: AsyncSession = Depends(get_db),
) -> InteractionOut:
    contact = await _get_contact_or_404(db, contact_id)

    if payload.interaction_type not in VALID_INTERACTION_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Type d'interaction invalide. Valeurs acceptées : {sorted(VALID_INTERACTION_TYPES)}",
        )

    now = datetime.now(timezone.utc)
    interaction = ContactInteraction(
        contact_id=contact.id,
        site_id=contact.site_id,
        user_id=current_user.id,
        interaction_type=payload.interaction_type,
        summary=payload.summary,
        result=payload.result,
        next_action=payload.next_action,
        followup_at=payload.followup_at,
        created_at=now,
    )
    db.add(interaction)

    # Cohérence automatique : la fiche contact reflète la dernière interaction
    # et la prochaine relance, sans double-saisie (sections 33-34).
    contact.last_contact_at = date.today()
    if payload.followup_at:
        contact.next_followup_at = payload.followup_at
    contact.updated_at = now

    await log_audit(
        db, user_id=current_user.id, entity="contact_interactions", entity_id=None,
        action="CREATE", field="interaction_type", new_value=payload.interaction_type,
    )
    await db.commit()
    await db.refresh(interaction)
    return InteractionOut.model_validate(interaction)


@router.get("/contacts/{contact_id}/interactions", response_model=list[InteractionOut])
async def list_interactions(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InteractionOut]:
    await _get_contact_or_404(db, contact_id)
    result = await db.execute(
        select(ContactInteraction)
        .where(ContactInteraction.contact_id == contact_id)
        .order_by(ContactInteraction.created_at.desc())
    )
    return [InteractionOut.model_validate(i) for i in result.scalars().all()]
