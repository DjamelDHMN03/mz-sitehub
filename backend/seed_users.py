import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import Role, User

USERS_TO_SEED = [
    {
        "email": "djamel.dahmane@mzbuilding.dz",
        "password": "mzbuilding2026",
        "first_name": "Djamel",
        "last_name": "Dahmane",
    },
    {
        "email": "djamel.henni@mzbuilding.dz",
        "password": "djamel.henni2026",
        "first_name": "Djamel",
        "last_name": "Henni",
    },
    {
        "email": "anis.abdeltif@mzbuilding.dz",
        "password": "anis.abdeltif2026",
        "first_name": "Anis",
        "last_name": "Abdeltif",
    },
]


async def _pick_role_id(session) -> int:
    roles = (await session.execute(select(Role).order_by(Role.id.asc()))).scalars().all()
    if not roles:
        raise RuntimeError("Aucun rôle trouvé dans la table `roles`. Vérifie l'initialisation des rôles.")
    for preferred in ("ADMIN", "MANAGER", "USER"):
        for r in roles:
            if (r.code or "").upper() == preferred:
                return r.id
    return roles[0].id


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        role_id = await _pick_role_id(session)
        for item in USERS_TO_SEED:
            email = item["email"].strip().lower()
            stmt = select(User).where(User.email == email)
            user = (await session.execute(stmt)).scalar_one_or_none()
            pw_hash = hash_password(item["password"])

            if user is None:
                user = User(
                    email=email,
                    password_hash=pw_hash,
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    role_id=role_id,
                    is_active=True,
                )
                session.add(user)
                print(f"[CREATED] {email}")
            else:
                user.password_hash = pw_hash
                user.first_name = item["first_name"]
                user.last_name = item["last_name"]
                user.is_active = True
                if not user.role_id:
                    user.role_id = role_id
                print(f"[UPDATED] {email}")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
