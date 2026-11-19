"""
Dépendances d'authentification et de permissions (RBAC).

Principe (section 11 & 82 du cahier des charges) : les permissions sont
appliquées côté BACKEND, jamais seulement côté frontend. `roles.permissions`
est un JSON du type :
    {"all": true}
    {"sites": "write", "contracts": "write", "users": "read"}
    {"sites": "write_own", "contacts": "write_own"}
    {"*": "read"}

`require_permission("sites", "write")` bloque la requête (403) si le rôle de
l'utilisateur n'accorde pas ce niveau d'accès sur cette ressource.
"""
import uuid
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidTokenError, decode_token, ACCESS_TOKEN_TYPE
from app.db.session import get_db
from app.models.user import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

PermissionLevel = Literal["read", "write", "write_own"]

# Ordre de "force" des niveaux : write > write_own > read
_LEVEL_RANK = {"read": 1, "write_own": 2, "write": 3}


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou désactivé",
        )
    return user


def require_permission(resource: str, level: PermissionLevel):
    """Factory de dépendance FastAPI vérifiant une permission sur une ressource."""

    async def _checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        result = await db.execute(select(Role).where(Role.id == current_user.role_id))
        role = result.scalar_one()
        perms: dict = role.permissions or {}

        if perms.get("all") is True:
            return current_user

        granted = perms.get(resource) or perms.get("*")
        if granted is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé sur '{resource}'",
            )

        if _LEVEL_RANK.get(granted, 0) < _LEVEL_RANK.get(level, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission insuffisante sur '{resource}' (requis: {level})",
            )
        return current_user

    return _checker
