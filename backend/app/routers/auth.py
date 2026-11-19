"""
Routeur /auth — login, refresh token, utilisateur courant, changement de mot de passe.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import login_rate_limiter
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    ACCESS_TOKEN_TYPE,
    InvalidTokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token_pair(user: User) -> TokenPair:
    access = create_token(str(user.id), token_type=ACCESS_TOKEN_TYPE)
    refresh = create_token(str(user.id), token_type=REFRESH_TOKEN_TYPE)
    return TokenPair(access_token=access, refresh_token=refresh)


async def _user_public(db: AsyncSession, user: User) -> UserPublic:
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one()
    return UserPublic(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role_code=role.code,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    rate_limit_key = payload.email.lower()

    if login_rate_limiter.is_blocked(rate_limit_key):
        wait_seconds = login_rate_limiter.seconds_until_unblocked(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trop de tentatives échouées. Réessayez dans {wait_seconds} secondes.",
        )

    result = await db.execute(
        select(User).where(User.email == payload.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    # Message volontairement générique : ne pas révéler si l'email existe (sécurité, section 82)
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email ou mot de passe incorrect",
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        login_rate_limiter.record_failed_attempt(rate_limit_key)
        raise invalid_credentials

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé — contactez un administrateur",
        )

    login_rate_limiter.reset(rate_limit_key)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return _issue_token_pair(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    import uuid as _uuid

    result = await db.execute(
        select(User).where(
            User.id == _uuid.UUID(token_payload["sub"]), User.deleted_at.is_(None)
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur invalide"
        )

    return _issue_token_pair(user)


@router.get("/me", response_model=UserPublic)
async def me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserPublic:
    return await _user_public(db, current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
