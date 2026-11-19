"""
Script de découverte pour MZ Sitehub.
Se connecte à l'API locale, récupère les listes de wilayas/communes/statuts
et les affiche pour qu'on puisse construire le mapping d'import.

UTILISATION :
1. Modifie EMAIL et PASSWORD ci-dessous avec tes identifiants MZ Sitehub.
2. Lance-le depuis le dossier backend, avec le venv activé :
   python discover_reference_data.py
3. Colle-moi tout ce qui s'affiche dans le terminal.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# === À MODIFIER ===
EMAIL = "TON_EMAIL_ICI"
PASSWORD = "TON_MOT_DE_PASSE_ICI"
# ==================


def try_login():
    """Essaie plusieurs chemins de login courants."""
    candidates = ["/auth/login", "/login", "/api/auth/login", "/api/login"]
    for path in candidates:
        try:
            resp = requests.post(
                BASE_URL + path,
                json={"email": EMAIL, "password": PASSWORD},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token") or data.get("token")
                if token:
                    print(f"[OK] Login réussi via {path}")
                    return token
            else:
                print(f"[--] {path} -> {resp.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[--] {path} -> erreur de connexion ({e})")
    return None


def try_get(path, headers):
    """Essaie de récupérer une ressource, gère les variantes de chemin."""
    variants = [path, "/api" + path]
    for p in variants:
        try:
            resp = requests.get(BASE_URL + p, headers=headers, timeout=5)
            if resp.status_code == 200:
                print(f"\n=== {p} ===")
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False)[:3000])
                return
            else:
                print(f"[--] {p} -> {resp.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[--] {p} -> erreur de connexion ({e})")
    print(f"[X] Impossible de récupérer {path}")


if __name__ == "__main__":
    print("Connexion à", BASE_URL)
    token = try_login()

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        print("\n[!] Pas de token récupéré — on essaie quand même sans authentification.\n")

    for path in ["/wilayas", "/communes", "/statuses", "/status"]:
        try_get(path, headers)

    print("\nTerminé. Copie-colle tout ce bloc dans la conversation.")
