"""
Découverte des endpoints liés aux "Doc B" et aux documents dans MZ Sitehub.

UTILISATION :
1. Modifie EMAIL et PASSWORD ci-dessous.
2. Lance :
     python discover_docb_endpoints.py
3. Colle-moi tout ce qui s'affiche.
"""

import json
import sys

import requests

BASE_URL = "http://localhost:8000"

# === À MODIFIER ===
EMAIL = "admin@mzbuilding.dz"
PASSWORD = "MzBuilding2026!"
# ==================


def login():
    resp = requests.post(BASE_URL + "/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=5)
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_openapi():
    resp = requests.get(BASE_URL + "/openapi.json", timeout=5)
    resp.raise_for_status()
    return resp.json()


def main():
    token = login()
    print("[OK] Login réussi\n")
    headers = {"Authorization": f"Bearer {token}"}

    spec = get_openapi()
    paths = spec.get("paths", {})

    print("=== Endpoints contenant 'doc', 'document' ou 'site-doc' ===\n")
    relevant = []
    for path, methods in paths.items():
        lower = path.lower()
        if "doc" in lower:
            for method, details in methods.items():
                summary = details.get("summary", "")
                print(f"{method.upper():6} {path}   -- {summary}")
                relevant.append((method.upper(), path))
    print()

    # Essaie de lister les documents existants pour un site connu (BL0711)
    print("=== Test d'appels GET pertinents ===\n")
    for method, path in relevant:
        if method != "GET":
            continue
        if "{" in path:
            continue  # on saute les routes avec paramètres pour ce test simple
        try:
            resp = requests.get(BASE_URL + path, headers=headers, timeout=5)
            print(f"GET {path} -> {resp.status_code}")
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
                except Exception:
                    pass
            print()
        except requests.exceptions.RequestException as e:
            print(f"GET {path} -> erreur : {e}\n")

    # Affiche aussi le schéma des payloads utiles s'ils existent
    print("=== Schémas liés à Doc B ===\n")
    schemas = spec.get("components", {}).get("schemas", {})
    for name in schemas:
        if "doc" in name.lower():
            print(f"--- {name} ---")
            print(json.dumps(schemas[name], indent=2, ensure_ascii=False)[:2000])
            print()


if __name__ == "__main__":
    main()
