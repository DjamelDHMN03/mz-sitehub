"""
Pour chaque doc B trouvé dans New Sites :
1. Retrouve le site correspondant dans MZ Sitehub via son code (ex: AL2338)
2. Upload le fichier Excel doc B comme document attaché à ce site
3. Crée la fiche "Doc B" (référence, organisme, date, statut, observation)
   en la liant au document uploadé

UTILISATION :
1. Vérifie EMAIL, PASSWORD, SITES_ROOT ci-dessous.
2. Lance d'abord en mode aperçu (rien n'est envoyé) :
     python import_docb_records.py
   Ça affiche ce qui serait fait, site par site.
3. Une fois vérifié, relance avec :
     python import_docb_records.py --confirm
   Ça fait réellement les uploads et créations.

Nécessite : pip install requests openpyxl
"""

import argparse
import sys
from pathlib import Path

import openpyxl
import requests

BASE_URL = "http://localhost:8000"
EMAIL = "admin@mzbuilding.dz"
PASSWORD = "MzBuilding2026!"
SITES_ROOT = r"C:\Users\WINDOWS 11\OneDrive\Desktop\New Sites"
DEFAULT_STATUS = "Préparé"  # ajuste si besoin, c'est un champ texte libre


def login():
    resp = requests.post(BASE_URL + "/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=5)
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_all_sites(headers):
    """Récupère la liste de tous les sites, gère une éventuelle pagination."""
    all_sites = []
    page = 1
    while True:
        resp = requests.get(BASE_URL + "/sites", headers=headers, params={"page": page, "limit": 200}, timeout=10)
        if resp.status_code != 200:
            # essaie sans pagination si l'API ne la supporte pas
            resp = requests.get(BASE_URL + "/sites", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", data) if isinstance(data, dict) else data
            all_sites.extend(items)
            break
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        if not items:
            break
        all_sites.extend(items)
        if len(items) < 200:
            break
        page += 1
    return all_sites


def build_code_to_id_map(sites):
    mapping = {}
    for s in sites:
        code = s.get("code")
        site_id = s.get("id")
        if code and site_id:
            mapping[code.strip().upper()] = site_id
    return mapping


def find_doc_b_files(root):
    root_path = Path(root)
    results = []
    for region_folder in root_path.iterdir():
        if not region_folder.is_dir():
            continue
        for site_folder in region_folder.iterdir():
            if not site_folder.is_dir():
                continue
            matches = (
                list(site_folder.rglob("docb_*.xlsx"))
                + list(site_folder.rglob("DOCB_*.xlsx"))
                + list(site_folder.rglob("DocB_*.xlsx"))
                + list(site_folder.rglob("Docb_*.xlsx"))
            )
            matches = list(dict.fromkeys(matches))
            for m in matches:
                results.append((region_folder.name, site_folder.name, m))
    return results


def read_basic_info(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    data = {
        "site_id_code": ws["A5"].value,
        "societe": ws["H11"].value,
        "date_visite": ws["H12"].value,
    }
    wb.close()
    return data


def upload_document(site_uuid, xlsx_path, headers):
    with open(xlsx_path, "rb") as f:
        files = {"file": (xlsx_path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = requests.post(
            f"{BASE_URL}/sites/{site_uuid}/documents",
            headers=headers,
            files=files,
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()


def create_doc_b(site_uuid, document_id, doc_data, headers):
    payload = {
        "reference": str(doc_data.get("site_id_code") or "").strip(),
        "organisme": doc_data.get("societe"),
        "status": DEFAULT_STATUS,
        "document_id": document_id,
        "date_depot": None,
        "date_preparation": None,
        "observation": None,
    }
    resp = requests.post(
        f"{BASE_URL}/sites/{site_uuid}/doc-b",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    token = login()
    print("[OK] Login réussi")
    headers = {"Authorization": f"Bearer {token}"}

    print("[INFO] Récupération de la liste des sites...")
    sites = fetch_all_sites(headers)
    code_to_id = build_code_to_id_map(sites)
    print(f"[OK] {len(code_to_id)} sites trouvés dans la base\n")

    doc_b_files = find_doc_b_files(SITES_ROOT)
    print(f"[INFO] {len(doc_b_files)} fichier(s) doc B trouvé(s) sur le disque\n")

    n_ok, n_skip = 0, 0
    for region, site_folder, xlsx_path in doc_b_files:
        label = f"{region} / {site_folder} / {xlsx_path.name}"
        try:
            info = read_basic_info(xlsx_path)
        except Exception as e:
            print(f"[X] {label} -> erreur lecture : {e}")
            n_skip += 1
            continue

        code = str(info.get("site_id_code") or "").strip().upper()
        site_uuid = code_to_id.get(code)

        if not site_uuid:
            print(f"[!] {label} -> code '{code}' introuvable dans MZ Sitehub, ignoré")
            n_skip += 1
            continue

        if not args.confirm:
            print(f"[APERÇU] {label} -> site {code} ({site_uuid}) : upload + création fiche Doc B")
            n_ok += 1
            continue

        try:
            doc = upload_document(site_uuid, xlsx_path, headers)
            document_id = doc.get("id")
            create_doc_b(site_uuid, document_id, info, headers)
            print(f"[OK] {label} -> importé pour le site {code}")
            n_ok += 1
        except requests.exceptions.HTTPError as e:
            print(f"[X] {label} -> erreur API : {e.response.status_code} {e.response.text[:200]}")
            n_skip += 1
        except Exception as e:
            print(f"[X] {label} -> erreur : {e}")
            n_skip += 1

    print(f"\nTerminé. {n_ok} traités, {n_skip} ignorés/échoués.")
    if not args.confirm:
        print("Mode aperçu seulement. Relance avec --confirm pour importer réellement.")


if __name__ == "__main__":
    main()
