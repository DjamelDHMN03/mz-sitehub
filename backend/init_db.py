import asyncio
import uuid
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import Base, engine
from app.models.user import Role, User


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Base et tables initialisées proprement.")


async def create_admin():
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        mapper = inspect(Role)
        role_columns = [c.key for c in mapper.column_attrs]

        res = await session.execute(select(Role).where(Role.code == "ADMIN"))
        role = res.scalar_one_or_none()

        # On utilise des chaînes de caractères pour l'ID (compatible SQLite)
        role_id_str = str(uuid.uuid4())
        user_id = uuid.uuid4()

        if not role:
            role_data = {"id": role_id_str, "code": "ADMIN"}
            if "label" in role_columns:
                role_data["label"] = "Administrator"
            if "name" in role_columns:
                role_data["name"] = "Administrator"
            if "permissions" in role_columns:
                role_data["permissions"] = "{}"

            role = Role(**role_data)
            session.add(role)
            await session.commit()
        else:
            role_id_str = str(role.id)

        res_user = await session.execute(
            select(User).where(User.email == "djamel.dahmane@mzbuilding.dz")
        )
        user = res_user.scalar_one_or_none()

        hashed_pwd = hash_password("mzbuilding2025")
        if not user:
            user = User(
                id=user_id,
                email="djamel.dahmane@mzbuilding.dz",
                password_hash=hashed_pwd,
                first_name="Djamel Eddine",
                last_name="Dahmane",
                role_id=role_id_str,
                is_active=True,
            )
            session.add(user)
            print("Administrateur créé avec succès !")
        else:
            user.password_hash = hashed_pwd
            user.role_id = role_id_str
            user.is_active = True
            print("Administrateur mis à jour avec succès !")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(init())
    asyncio.run(create_admin())