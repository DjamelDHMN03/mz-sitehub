import asyncio
import asyncpg
import secrets
import string
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

env_lines = open('.env', encoding='utf-8').read().splitlines()
db_url_line = next(l for l in env_lines if l.startswith('DATABASE_URL'))
db_url = db_url_line.split('=', 1)[1].strip().replace('+asyncpg', '')

COMPTES = [
    ('djamel.henni@mzbuilding.dz', 'Djamel', 'HENNI'),
    ('anis.abdeltif@mzbuilding.dz', 'Anis', 'ABDELTIF'),
]

async def create_users():
    conn = await asyncpg.connect(db_url)
    roles = await conn.fetch('select id, code from roles order by code')
    print("Rôles disponibles :", [dict(r) for r in roles])
    
    target_role = next((r for r in roles if r['code'].lower() in ['user', 'charge', 'standard', 'collaborateur']), roles[0])
    print(f"Rôle attribué : {target_role['code']}")
    
    for email, prenom, nom in COMPTES:
        exists = await conn.fetchval('select 1 from users where email=$1', email)
        if exists:
            print(f"Compte déjà existant : {email} (ignoré)")
            continue
        
        pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        pw_hash = hash_password(pw)
        
        await conn.execute(
            '''
            insert into users (email, password_hash, first_name, last_name, role_id, is_active, created_at, updated_at)
            values ($1, $2, $3, $4, $5, true, now(), now())
            ''',
            email, pw_hash, prenom, nom, target_role['id']
        )
        print(f"SUCCÈS -> Email : {email} | Mot de passe généré : {pw}")
    
    await conn.close()

asyncio.run(create_users())
