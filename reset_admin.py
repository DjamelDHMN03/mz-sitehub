import sqlite3
import bcrypt

DB_PATH = "mz_local.db"

def reset_admin():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Recréation propre de la table avec la structure exacte attendue par SQLAlchemy
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            role_id TEXT,
            is_active BOOLEAN NOT NULL,
            last_login_at DATETIME,
            created_at DATETIME,
            updated_at DATETIME,
            deleted_at DATETIME
        )
    """)
    
    email = "djamel.dahmane@mzbuilding.dz"
    plain_password = "mzbuilding2025"
    
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    password_hash = hashed_bytes.decode('utf-8')
    
    # Vérifier si l'admin existe déjà
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, role_id = 'ADMIN', is_active = 1, deleted_at = NULL 
            WHERE email = ?
        """, (password_hash, email))
        print("Compte admin mis à jour avec succès !")
    else:
        cursor.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, role_id, is_active, deleted_at)
            VALUES (?, ?, 'Djamel Eddine', 'Dahmane', 'ADMIN', 1, NULL)
        """, (email, password_hash))
        print("Compte admin créé avec succès !")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset_admin()