"""
Utilitaire d'audit — à réutiliser par tous les modules (sites, contacts,
contrats, documents...) pour respecter la section 19 sans dupliquer la logique.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_audit(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    entity: str,
    entity_id: uuid.UUID | None,
    action: str,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    """Ajoute une ligne d'audit. Ne fait PAS le commit — c'est à l'appelant
    de committer avec le reste de sa transaction (atomicité)."""
    db.add(
        AuditLog(
            user_id=user_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            field=field,
            old_value=old_value,
            new_value=new_value,
            occurred_at=datetime.now(timezone.utc),
        )
    )
