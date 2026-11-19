"""Reinitialise le mot de passe d'un compte EXISTANT (ne cree jamais de compte).

Usage (depuis le dossier backend, venv active) :
    python -m scripts.reset_admin_password
Le mot de passe est demande a l'ecran (non affiche). Par defaut : admin@mzbuilding.dz
Options : --email autre@adresse.dz    ou variable d'environnement NEW_PW (mode automatique).
"""
import argparse
import asyncio
import getpass
import os
import sys

sys.path.insert(0, ".")

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def main(email: str, pw: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"Utilisateur introuvable : {email} - rien n'a ete modifie.")
            return
        user.password_hash = hash_password(pw)
        await db.commit()
        print("Mot de passe mis a jour pour", email)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="admin@mzbuilding.dz")
    args = parser.parse_args()
    pw = os.environ.get("NEW_PW")
    if not pw:
        pw = getpass.getpass("Nouveau mot de passe (8 caracteres minimum) : ")
        if pw != getpass.getpass("Confirmez le mot de passe : "):
            sys.exit("Les deux saisies sont differentes : annule.")
    if len(pw) < 8:
        sys.exit("Mot de passe trop court (8 caracteres minimum) : annule.")
    asyncio.run(main(args.email, pw))
