"""Routeur /users - comptes utilisateurs, negociateurs freelance et options."""
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import Role, User

router = APIRouter(prefix="/users", tags=["users"])

LIST_ROLES = {"ADMIN", "MANAGER"}
# Negociateur freelance : pas de connexion possible (e-mail factice, mot de passe aleatoire inconnu)
NOLOGIN_DOMAIN = "@sans-compte.local"
NOLOGIN_LABEL = "Sans compte (freelance)"


class UserOption(BaseModel):
    id: uuid.UUID
    full_name: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    role_code: str
    is_active: bool


class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role_code: str = "ACQUISITION"


class FreelanceCreate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)


class UserPatch(BaseModel):
    is_active: bool | None = None


def _to_out(user: User, role_code: str) -> UserOut:
    email = str(user.email)
    return UserOut(
        id=user.id,
        email=NOLOGIN_LABEL if email.endswith(NOLOGIN_DOMAIN) else email,
        first_name=user.first_name,
        last_name=user.last_name,
        role_code=role_code,
        is_active=user.is_active,
    )


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


@router.get("", response_model=list[UserOut])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    my_role = (
        await db.execute(select(Role.code).where(Role.id == current_user.role_id))
    ).scalar_one_or_none()
    if my_role not in LIST_ROLES:
        raise HTTPException(status_code=403, detail="Acces reserve aux administrateurs et managers")
    rows = (
        await db.execute(
            select(User, Role.code)
            .join(Role, Role.id == User.role_id)
            .where(User.deleted_at.is_(None))
            .order_by(User.first_name, User.last_name)
        )
    ).all()
    return [_to_out(u, code) for u, code in rows]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission("users", "write")),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    email = payload.email.strip().lower()
    if "@" not in email or " " in email or email.endswith(NOLOGIN_DOMAIN):
        raise HTTPException(status_code=400, detail="Adresse e-mail invalide")
    exists = (await db.execute(select(User.id).where(func.lower(User.email) == email))).first()
    if exists:
        raise HTTPException(status_code=409, detail="Un compte existe deja avec cet e-mail")
    role = (await db.execute(select(Role).where(Role.code == payload.role_code))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=400, detail="Role inconnu")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=(payload.first_name or "").strip() or None,
        last_name=(payload.last_name or "").strip() or None,
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await log_audit(
        db, user_id=current_user.id, entity="users", entity_id=user.id,
        action="CREATE", new_value=email,
    )
    await db.commit()
    await db.refresh(user)
    return _to_out(user, role.code)


@router.post("/freelance", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_freelance(
    payload: FreelanceCreate,
    current_user: User = Depends(require_permission("users", "write")),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Negociateur freelance : sans e-mail ni mot de passe saisis, sans connexion possible."""
    first = (payload.first_name or "").strip() or None
    last = (payload.last_name or "").strip() or None
    if not first and not last:
        raise HTTPException(status_code=400, detail="Indiquez au moins un nom ou un prenom")
    role = (await db.execute(select(Role).where(Role.code == "LECTURE"))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=500, detail="Role LECTURE introuvable")

    user = User(
        email=f"freelance-{uuid.uuid4().hex[:12]}{NOLOGIN_DOMAIN}",
        password_hash=hash_password(secrets.token_urlsafe(32)),
        first_name=first,
        last_name=last,
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await log_audit(
        db, user_id=current_user.id, entity="users", entity_id=user.id,
        action="CREATE", new_value=f"freelance: {first or ''} {last or ''}".strip(),
    )
    await db.commit()
    await db.refresh(user)
    return _to_out(user, role.code)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserPatch,
    current_user: User = Depends(require_permission("users", "write")),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = (
        await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if payload.is_active is not None and payload.is_active != user.is_active:
        if user.id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Vous ne pouvez pas desactiver votre propre compte")
        await log_audit(
            db, user_id=current_user.id, entity="users", entity_id=user.id,
            action="UPDATE", field="is_active",
            old_value=str(user.is_active), new_value=str(payload.is_active),
        )
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    role_code = (await db.execute(select(Role.code).where(Role.id == user.role_id))).scalar_one()
    return _to_out(user, role_code)