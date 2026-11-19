"""
Import automatique des fichiers "doc B" (Excel) vers MZ Sitehub.

UTILISATION :
1. Modifie EMAIL, PASSWORD et SITES_ROOT ci-dessous.
2. Lance d'abord en mode "aperçu" (aucune donnée n'est envoyée) :
     python import_sites.py
   Ça génère un fichier import_preview.csv à vérifier.
3. Une fois que tu as vérifié le CSV et que tout est correct, relance avec :
     python import_sites.py --confirm
   Ça envoie réellement les sites à l'API.

Nécessite : pip install requests openpyxl unidecode
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import openpyxl
import requests

try:
    from unidecode import unidecode
except ImportError:
    print("Le paquet 'unidecode' n'est pas installé. Lance : pip install unidecode")
    sys.exit(1)


# ============ À MODIFIER ============
BASE_URL = "http://localhost:8000"
EMAIL = "admin@mzbuilding.dz"
PASSWORD = "MzBuilding2026!"
SITES_ROOT = r"C:\Users\WINDOWS 11\OneDrive\Desktop\Bureau\New Sites"
DEFAULT_STATUS_NAME = "Nouveau"  # ajuste selon ce que renvoie /statuses
# =====================================


CELL_MAP = {
    "site_id": "A5",
    "candidat": "F5",
    "nom_site": "H5",
    "region": "B9",
    "wilaya": "B10",
    "daira": "B11",
    "commune": "B12",
    "negociateur": "H9",
    "negociateur_tel": "H10",
    "societe": "H11",
    "date_visite": "H12",
    "adresse": "A17",
    "proprietaire": "A20",
    "longitude": "K25",
    "latitude": "K26",
    "type_site": "A47",
    "type_environnement": "A50",
    "securite_zone": "A53",
}


def normalize(s):
    """Normalise un texte pour comparaison (minuscule, sans accents, trim)."""
    if s is None:
        return ""
    return unidecode(str(s)).strip().lower()


def login():
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
        except requests.exceptions.RequestException:
            pass
    print("[X] Login impossible. Vérifie EMAIL/PASSWORD et que le backend tourne.")
    sys.exit(1)


def fetch_reference(path_candidates, headers):
    """Essaie plusieurs chemins possibles pour une ressource de référence."""
    for path in path_candidates:
        for p in (path, "/api" + path):
            try:
                resp = requests.get(BASE_URL + p, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    # gère le cas où la réponse est enveloppée dans {"items": [...]}
                    if isinstance(data, dict):
                        for key in ("items", "results", "data"):
                            if key in data:
                                data = data[key]
                                break
                    print(f"[OK] {p} -> {len(data)} éléments")
                    return data
            except requests.exceptions.RequestException:
                pass
    print(f"[X] Aucun endpoint trouvé parmi {path_candidates}")
    return []


def build_name_id_map(items):
    """Construit un dict {nom_normalisé: id} à partir d'une liste d'objets."""
    mapping = {}
    for item in items:
        name = item.get("name") or item.get("nom") or item.get("libelle")
        item_id = item.get("id")
        if name and item_id is not None:
            mapping[normalize(name)] = item_id
    return mapping


def read_doc_b(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    data = {}
    for key, coord in CELL_MAP.items():
        data[key] = ws[coord].value
    wb.close()
    return data


def find_doc_b_files(root):
    """
    Parcourt deux niveaux : New Sites/<région>/<dossier de site>/docb_*.xlsx
    Retourne une liste de tuples (nom_region, nom_dossier_site, chemin_xlsx).
    """
    root_path = Path(root)
    results = []
    for region_folder in root_path.iterdir():
        if not region_folder.is_dir():
            continue
        for site_folder in region_folder.iterdir():
            if not site_folder.is_dir():
                continue
            matches = (
                list(site_folder.glob("docb_*.xlsx"))
                + list(site_folder.glob("DOCB_*.xlsx"))
                + list(site_folder.glob("DocB_*.xlsx"))
            )
            if matches:
                results.append((region_folder.name, site_folder.name, matches[0]))
            else:
                print(f"[!] Pas de doc B trouvé dans : {region_folder.name} / {site_folder.name}")
    return results


def build_payload(doc_data, wilaya_map, commune_map, status_id, region_folder_name=None):
    wilaya_id = wilaya_map.get(normalize(doc_data.get("wilaya")))
    if wilaya_id is None and region_folder_name:
        # filet de sécurité : essaie avec le nom du dossier région/wilaya
        wilaya_id = wilaya_map.get(normalize(region_folder_name))
    commune_id = commune_map.get(normalize(doc_data.get("commune")))

    payload = {
        "name": doc_data.get("nom_site"),
        "code": doc_data.get("site_id"),
        "wilaya_id": wilaya_id,
        "commune_id": commune_id,
        "address": doc_data.get("adresse"),
        "latitude": doc_data.get("latitude"),
        "longitude": doc_data.get("longitude"),
        "site_type": doc_data.get("type_site"),
        "owner_name": doc_data.get("proprietaire"),
        "organisme": doc_data.get("societe"),
        "status_id": status_id,
        "custom_fields": {
            "candidat": doc_data.get("candidat"),
            "region": doc_data.get("region"),
            "daira": doc_data.get("daira"),
            "negociateur": doc_data.get("negociateur"),
            "negociateur_tel": doc_data.get("negociateur_tel"),
            "date_visite": str(doc_data.get("date_visite")) if doc_data.get("date_visite") else None,
            "type_environnement": doc_data.get("type_environnement"),
            "securite_zone": doc_data.get("securite_zone"),
        },
    }
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Envoie réellement les sites à l'API")
    args = parser.parse_args()

    token = login()
    headers = {"Authorization": f"Bearer {token}"}

    wilayas = fetch_reference(["/wilayas", "/wilaya"], headers)
    communes = fetch_reference(["/communes", "/commune"], headers)
    statuses = fetch_reference(["/statuses", "/status", "/site-statuses"], headers)

    wilaya_map = build_name_id_map(wilayas)
    commune_map = build_name_id_map(communes)
    status_map = build_name_id_map(statuses)

    status_id = status_map.get(normalize(DEFAULT_STATUS_NAME))
    if status_id is None:
        print(f"[!] Statut par défaut '{DEFAULT_STATUS_NAME}' introuvable.")
        print(f"    Statuts disponibles : {list(status_map.keys())}")
        sys.exit(1)
    print(f"[OK] status_id par défaut = {status_id} ({DEFAULT_STATUS_NAME})")

    site_files = find_doc_b_files(SITES_ROOT)
    print(f"\n[INFO] {len(site_files)} dossier(s) de site avec doc B trouvé(s)\n")

    rows = []
    payloads = []
    for region_name, site_folder_name, xlsx_path in site_files:
        folder_name = f"{region_name} / {site_folder_name}"
        try:
            doc_data = read_doc_b(xlsx_path)
        except Exception as e:
            print(f"[X] Erreur lecture {folder_name} : {e}")
            continue

        payload = build_payload(doc_data, wilaya_map, commune_map, status_id, region_folder_name=region_name)

        issues = []
        if not payload["code"]:
            issues.append("code manquant")
        if not payload["name"]:
            issues.append("name manquant")
        if payload["wilaya_id"] is None:
            issues.append(f"wilaya '{doc_data.get('wilaya')}' non trouvée")
        if payload["commune_id"] is None:
            issues.append(f"commune '{doc_data.get('commune')}' non trouvée")

        row = dict(payload)
        row["custom_fields"] = str(row["custom_fields"])
        row["dossier"] = folder_name
        row["problemes"] = "; ".join(issues) if issues else "OK"
        rows.append(row)

        if not issues:
            payloads.append((folder_name, payload))

    # Écrit le CSV d'aperçu
    preview_path = "import_preview.csv"
    fieldnames = ["dossier", "problemes"] + [k for k in rows[0].keys() if k not in ("dossier", "problemes")] if rows else []
    with open(preview_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[OK] Aperçu écrit dans {preview_path} ({len(rows)} sites analysés, {len(payloads)} prêts à importer)")

    if not args.confirm:
        print("\nMode aperçu seulement. Vérifie le CSV, puis relance avec --confirm pour importer réellement.")
        return

    print(f"\n[IMPORT] Envoi de {len(payloads)} sites à l'API...\n")
    success, failed = 0, 0
    for folder_name, payload in payloads:
        try:
            resp = requests.post(BASE_URL + "/sites", json=payload, headers=headers, timeout=10)
            if resp.status_code in (200, 201):
                print(f"[OK] {folder_name} -> créé")
                success += 1
            else:
                print(f"[X] {folder_name} -> {resp.status_code} : {resp.text[:200]}")
                failed += 1
        except requests.exceptions.RequestException as e:
            print(f"[X] {folder_name} -> erreur réseau : {e}")
            failed += 1

    print(f"\nTerminé. {success} réussis, {failed} échoués.")


if __name__ == "__main__":
    main()
