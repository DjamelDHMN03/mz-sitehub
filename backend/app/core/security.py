"""
Sécurité MZ SITEHUB : hash de mot de passe (bcrypt via passlib) et JWT maison.

Choix technique (décision Phase 3) : JWT fait maison plutôt que Supabase Auth,
pour rester à 0 DA et garder un contrôle total sur les rôles/permissions
côté backend (voir section 82 du cahier des charges : RBAC, validation backend).
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import bcrypt

from app.core.config import get_settings

settings = get_settings()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(plain_password: str) -> str:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def create_token(
    subject: str,
    token_type: str = ACCESS_TOKEN_TYPE,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Crée un JWT signé. `subject` = id utilisateur (UUID en string)."""
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.jwt_expiration_minutes
            if token_type == ACCESS_TOKEN_TYPE
            else settings.jwt_expiration_minutes * 6  # refresh token plus long
        )

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    pass


def decode_token(token: str, expected_type: str = ACCESS_TOKEN_TYPE) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError("Token invalide ou expiré") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Type de token inattendu (attendu: {expected_type})")

    return payload
