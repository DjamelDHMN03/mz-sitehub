"""
Script de seed — crée le premier compte ADMIN si aucun utilisateur n'existe.

Usage (depuis le conteneur backend ou un venv local avec les mêmes dépendances) :
    python -m scripts.seed_admin --email admin@mzbuilding.dz --password "changez-moi"

Ce script ne fait JAMAIS de suppression ni d'écrasement : si un utilisateur existe
déjà avec cet email, il s'arrête sans rien modifier.
"""
import argparse
import asyncio
import sys

sys.path.insert(0, ".")  # pour exécution directe depuis backend/

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import Role, User


async def seed_admin(email: str, password: str, first_name: str, last_name: str) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"⚠️  Un utilisateur existe déjà avec l'email {email} — rien à faire.")
            return

        admin_role = await db.execute(select(Role).where(Role.code == "ADMIN"))
        role = admin_role.scalar_one_or_none()
        if role is None:
            print("❌ Le rôle ADMIN n'existe pas — la migration 001 a-t-elle bien été appliquée ?")
            return

        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role_id=role.id,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"✅ Compte ADMIN créé : {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Créer le premier compte ADMIN MZ SITEHUB")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--first-name", default="Admin")
    parser.add_argument("--last-name", default="MZ SITEHUB")
    args = parser.parse_args()

    asyncio.run(seed_admin(args.email, args.password, args.first_name, args.last_name))
