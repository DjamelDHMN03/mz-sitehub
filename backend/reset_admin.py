import sqlite3
import bcrypt
import uuid

DB_PATH = "mz_local.db"

def reset_admin():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. S'assurer que la table roles existe avec un rôle admin par défaut
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT
        )
    """)
    
    # 2. S'assurer que la table users existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            role_id TEXT,
            is_active BOOLEAN NOT NULL,
            last_login_at DATETIME,
            created_at DATETIME,
            updated_at DATETIME,
            deleted_at DATETIME,
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    """)
    
    # Créer un ID fixe pour le rôle ADMIN
    role_admin_id = "00000000-0000-0000-0000-000000000099"
    cursor.execute("""
        INSERT OR IGNORE INTO roles (id, code, name)
        VALUES (?, 'ADMIN', 'Administrator')
    """, (role_admin_id,))
    
    email = "djamel.dahmane@mzbuilding.dz"
    plain_password = "mzbuilding2025"
    
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    password_hash = hashed_bytes.decode('utf-8')
    
    admin_id = str(uuid.uuid4())
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, role_id = ?, is_active = 1, deleted_at = NULL 
            WHERE email = ?
        """, (password_hash, role_admin_id, email))
        print("Compte admin mis à jour avec succès !")
    else:
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, first_name, last_name, role_id, is_active, deleted_at)
            VALUES (?, ?, ?, 'Djamel Eddine', 'Dahmane', ?, 1, NULL)
        """, (admin_id, email, password_hash, role_admin_id))
        print("Compte admin créé avec succès !")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset_admin()