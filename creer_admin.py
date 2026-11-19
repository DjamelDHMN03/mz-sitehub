import asyncio
import os
import bcrypt
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def create_admin():
    print(f"Connexion à la base de données...")
    
    # Génération du hash sécurisé avec bcrypt directement
    plain_password = "mzbuilding2025"
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')
    
    email = "djamel.dahmane@mzbuilding.dz"
    
    # Connexion au moteur asynchrone SQLAlchemy
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        # Vérifier si l'utilisateur existe déjà
        result = await conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()
        
        if user:
            # Mettre à jour le mot de passe si l'utilisateur existe déjà
            await conn.execute(
                text("UPDATE users SET password_hash = :ph, is_active = TRUE WHERE email = :email"),
                {"ph": hashed_password, "email": email}
            )
            print(f"✅ Compte administrateur existant mis à jour avec succès pour : {email}")
        else:
            # Récupérer l'ID du rôle ADMIN
            role_result = await conn.execute(
                text("SELECT id FROM roles WHERE code = 'ADMIN'")
            )
            role_row = role_result.fetchone()
            
            if not role_row:
                print("❌ Erreur : Rôle 'ADMIN' introuvable dans la table roles.")
                return
                
            role_id = role_row[0]
            
            # Insérer le nouvel utilisateur admin
            await conn.execute(
                text("""
                    INSERT INTO users (email, password_hash, first_name, last_name, role_id, is_active, created_at, updated_at) 
                    VALUES (:email, :ph, :fn, :ln, :rid, TRUE, NOW(), NOW())
                """),
                {
                    "email": email, 
                    "ph": hashed_password, 
                    "fn": "DAHMANE", 
                    "ln": "DJAMEL EDDINE", 
                    "rid": role_id
                }
            )
            print(f"🎉 Compte administrateur créé avec succès pour : {email}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_admin())