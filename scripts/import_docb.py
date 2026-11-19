#!/usr/bin/env python3
"""
import_docb.py - Import automatique des fichiers "doc B" (Excel) vers MZ SITEHUB.

Usage :
    # Dry-run : affiche ce qui serait importe, genere un CSV recapitulatif
    python import_docb.py

    # Import reel (apres validation du dry-run)
    python import_docb.py --confirm

    # Dossier personnalise (defaut : dossier ALGER)
    python import_docb.py --dossier "C:/chemin/vers/dossier"

    # Statut different (defaut : 5 = "Doc B depose")
    python import_docb.py --status-id 3 --confirm

Prerequis :
    pip install openpyxl requests asyncpg sqlalchemy[asyncio]

Endpoints utilises :
    POST /auth/login          -> token JWT
    POST /sites               -> creer un site
    DB directe                -> resolution wilaya_id / commune_id
"""

import argparse
import asyncio
import csv
import os
import re
import signal
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import openpyxl
import requests
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ========================================================================
# Configuration
# ========================================================================

_BACKEND_ENV = Path(__file__).parent.parent / "backend" / ".env"

# Chemin vers le dossier backend (venv + uvicorn)
_BACKEND_DIR = Path(__file__).parent.parent / "backend"
_VENV_PYTHON  = _BACKEND_DIR / "venv" / "Scripts" / "python.exe"
_UVICORN_CMD  = ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

DEFAULT_SITES_DIR = Path(r"C:\Users\WINDOWS 11\OneDrive\Desktop\New Sites\ALGER")
API_BASE = "http://localhost:8000"
DEFAULT_EMAIL = "admin@mzsitehub.dz"
DEFAULT_PASSWORD = "Admin2026!"

# 5 = "Doc B depose" - statut par defaut pour les sites qui ont un doc B
DEFAULT_STATUS_ID = 5

# Processus backend si on l'a demarre nous-memes (pour cleanup a la fin)
_backend_proc = None


# ========================================================================
# Demarrage automatique du backend
# ========================================================================

def _is_backend_alive(api_base: str, timeout: float = 2.0) -> bool:
    """Retourne True si le backend repond sur /health."""
    try:
        r = requests.get(f"{api_base}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def ensure_backend_running(api_base: str) -> bool:
    """
    Verifie si le backend est deja en marche.
    Si non, le demarre dans un sous-processus et attend qu il soit pret.
    Retourne True si le backend est disponible, False en cas d echec.
    """
    global _backend_proc

    # --- Deja actif ? ---
    if _is_backend_alive(api_base):
        print("  OK : backend deja en cours d execution.")
        return True

    # --- Demarrage automatique ---
    print("  Backend non detecte. Demarrage automatique...")

    if not _VENV_PYTHON.exists():
        print(f"  [ERREUR] venv introuvable : {_VENV_PYTHON}")
        print("           Activez le venv manuellement et relancez.")
        return False

    # Construire la commande avec le python du venv
    cmd = [str(_VENV_PYTHON), "-m"] + _UVICORN_CMD

    try:
        _backend_proc = subprocess.Popen(
            cmd,
            cwd=str(_BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            # Nouveau groupe de processus pour pouvoir killer proprement
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
    except Exception as e:
        print(f"  [ERREUR] Impossible de lancer le backend : {e}")
        return False

    print(f"  PID backend : {_backend_proc.pid}")
    print("  Attente du demarrage (jusqu a 30s)...", end="", flush=True)

    # Attendre que /health reponde (max 30s, polling toutes les secondes)
    for _ in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        if _backend_proc.poll() is not None:
            # Processus mort prematurement
            out = _backend_proc.stdout.read() if _backend_proc.stdout else ""
            print(f"\n  [ERREUR] Le backend s est arrete (code {_backend_proc.returncode}).")
            if out:
                print("  Sortie :", out[:800])
            return False
        if _is_backend_alive(api_base):
            print(" OK !")
            return True

    print("\n  [ERREUR] Le backend n a pas repondu dans les 30 secondes.")
    return False


def stop_backend_if_started():
    """Arrete le backend si c est nous qui l avons demarre."""
    global _backend_proc
    if _backend_proc and _backend_proc.poll() is None:
        print("\n  Arret du backend (demarre par ce script)...")
        if sys.platform == "win32":
            _backend_proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            _backend_proc.terminate()
        try:
            _backend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _backend_proc.kill()
        print("  Backend arrete.")




# ========================================================================
# Helpers
# ========================================================================

def normalize(s):
    """Normalise une chaine : minuscules, sans accents, sans espaces superflus."""
    if not s:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s


def load_env(env_path):
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def dms_to_decimal(dms_str):
    """
    Convertit des coordonnees DMS (ex: 2 deg 54'33.38"E) en degres decimaux.
    Retourne None si la conversion echoue.
    """
    if not dms_str:
        return None
    s = str(dms_str).strip()
    # Regex acceptant differents separateurs (degre, prime, seconde)
    pattern = r"(\d+)[^\d]+(\d+)[^\d]+(\d+(?:[.,]\d+)?)[^\d]*([NSEWNOQ]?)"
    m = re.search(pattern, s, re.IGNORECASE)
    if not m:
        try:
            return float(s.replace(",", "."))
        except Exception:
            return None
    deg = float(m.group(1))
    mnt = float(m.group(2))
    sec = float(m.group(3).replace(",", "."))
    direction = m.group(4).upper()
    decimal = deg + mnt / 60 + sec / 3600
    if direction in ("S", "W", "O"):
        decimal = -decimal
    return round(decimal, 6)


def find_docb_file(folder):
    """Trouve le fichier docb_*.xlsx (insensible a la casse) dans un dossier."""
    for f in folder.iterdir():
        if f.is_file() and re.match(r"docb_.*\.xlsx$", f.name, re.IGNORECASE):
            return f
    return None


def extract_checked_value(ws, start_row, end_row, label_col, check_col):
    """
    Retourne le libelle (label_col) de la ligne ou check_col contient 'x' ou 'X'.
    """
    for row in range(start_row, end_row + 1):
        check_val = ws.cell(row=row, column=check_col).value
        if check_val and str(check_val).strip().upper() == "X":
            label = ws.cell(row=row, column=label_col).value
            if label:
                return str(label).strip().rstrip(":")
    return None


def clean_str(val):
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def parse_docb(xlsx_path):
    """
    Extrait toutes les donnees d'un fichier doc B selon le mapping de cellules.
    """
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)

    # Chercher la feuille Feuil1 (insensible a la casse)
    sheet_name = None
    for name in wb.sheetnames:
        if name.strip().lower() in ("feuil1", "feuille1", "sheet1", "feuil 1"):
            sheet_name = name
            break
    if sheet_name is None:
        sheet_name = wb.sheetnames[0]

    ws = wb[sheet_name]

    # --- Champs principaux ---
    site_id_raw = clean_str(ws["A5"].value)
    candidat    = clean_str(ws["F5"].value)
    nom_site    = clean_str(ws["H5"].value)
    region      = clean_str(ws["B9"].value)
    wilaya      = clean_str(ws["B10"].value)
    daira       = clean_str(ws["B11"].value)
    commune     = clean_str(ws["B12"].value)
    negociateur = clean_str(ws["H9"].value)
    tel_neg     = clean_str(ws["H10"].value)
    societe     = clean_str(ws["H11"].value)
    date_visite = clean_str(ws["H12"].value)
    adresse     = clean_str(ws["A17"].value)
    proprietaire = clean_str(ws["A20"].value)

    # --- GPS : conversion DMS -> decimal ---
    lon_raw  = clean_str(ws["K25"].value)
    lat_raw  = clean_str(ws["K26"].value)
    longitude = dms_to_decimal(lon_raw) if lon_raw else None
    latitude  = dms_to_decimal(lat_raw) if lat_raw else None

    # --- Type de site, environnement, securite ---
    type_site = clean_str(ws["A47"].value)
    type_env  = clean_str(ws["A50"].value)
    securite  = clean_str(ws["A53"].value)

    # --- Type de propriete : colonne C cochee (col=3), libelle en colonne D (col=4) ---
    type_propriete = extract_checked_value(ws, 23, 33, label_col=4, check_col=3)

    # --- Connexion Sonelgaz : colonne F cochee (col=6), libelle en colonne E (col=5) ---
    sonelgaz = extract_checked_value(ws, 84, 86, label_col=5, check_col=6)

    # Normaliser le code site
    code = site_id_raw.strip().upper() if site_id_raw else None

    # Construire custom_fields
    custom_fields = {}
    if candidat:     custom_fields["candidat"]           = candidat
    if region:       custom_fields["region"]             = region.strip()
    if daira:        custom_fields["daira"]              = daira.strip()
    if negociateur:  custom_fields["negociateur"]        = negociateur
    if tel_neg:      custom_fields["tel_negociateur"]    = str(tel_neg)
    if date_visite:  custom_fields["date_visite"]        = date_visite
    if type_env:     custom_fields["type_environnement"] = type_env.strip()
    if securite:     custom_fields["securite_zone"]      = securite
    if type_propriete: custom_fields["type_propriete"]   = type_propriete
    if sonelgaz:     custom_fields["connexion_sonelgaz"] = sonelgaz
    if lon_raw:      custom_fields["gps_brut_longitude"] = lon_raw
    if lat_raw:      custom_fields["gps_brut_latitude"]  = lat_raw

    return {
        "code":        code,
        "name":        nom_site,
        "wilaya_raw":  wilaya.strip() if wilaya else None,
        "commune_raw": commune.strip() if commune else None,
        "address":     adresse,
        "latitude":    latitude,
        "longitude":   longitude,
        "site_type":   type_site.strip() if type_site else None,
        "owner_name":  proprietaire,
        "organisme":   societe.strip() if societe else None,
        "custom_fields": custom_fields,
    }


# ========================================================================
# Resolution des references (wilaya_id, commune_id) via DB directe
# ========================================================================

async def load_reference_data(db_url):
    """
    Charge les mappings :
      wilaya_norm -> wilaya_id
      (wilaya_id, commune_norm) -> commune_id
    """
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        db_url = "postgresql+asyncpg://" + db_url.split("://", 1)[1]

    engine = create_async_engine(db_url)
    wilayas = {}
    communes = {}

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, name FROM wilayas"))
        for row in result:
            wilayas[normalize(row.name)] = row.id

        result = await conn.execute(text("SELECT id, wilaya_id, name FROM communes"))
        for row in result:
            key_norm = normalize(row.name)
            communes[(row.wilaya_id, key_norm)] = row.id
            if ("*", key_norm) not in communes:
                communes[("*", key_norm)] = row.id

    await engine.dispose()
    return wilayas, communes


# ========================================================================
# API helpers
# ========================================================================

def api_login(email, password, api_base):
    try:
        resp = requests.post(
            f"{api_base}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]
        print(f"[ERREUR] Login echoue ({resp.status_code}): {resp.text}")
        return None
    except Exception as e:
        print(f"[ERREUR] Connexion API impossible : {e}")
        return None


def api_create_site(payload, token, api_base):
    try:
        resp = requests.post(
            f"{api_base}/sites",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 201:
            return True, f"Cree avec id={resp.json().get('id', '?')}"
        elif resp.status_code == 409:
            return False, f"DOUBLON : code '{payload.get('code')}' deja existant"
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            return False, f"HTTP {resp.status_code}: {detail}"
    except Exception as e:
        return False, f"Erreur reseau: {e}"


# ========================================================================
# Scan des dossiers
# ========================================================================

def scan_sites_folder(sites_dir):
    found = []
    skipped = []

    if not sites_dir.exists():
        print(f"[ERREUR] Dossier introuvable : {sites_dir}")
        sys.exit(1)

    for sub in sorted(sites_dir.iterdir()):
        if not sub.is_dir():
            continue
        docb = find_docb_file(sub)
        if docb is None:
            # Chercher dans les sous-sous-dossiers
            for subsub in sub.iterdir():
                if subsub.is_dir():
                    docb2 = find_docb_file(subsub)
                    if docb2:
                        found.append((subsub, docb2))
            skipped.append(sub.name)
        else:
            found.append((sub, docb))

    if skipped:
        print(f"\n  Dossiers SANS doc B ignores ({len(skipped)}) :")
        for s in skipped:
            print(f"   - {s}")

    return found


# ========================================================================
# Main
# ========================================================================

def main():
    parser = argparse.ArgumentParser(description="Import doc B Excel -> MZ SITEHUB API")
    parser.add_argument("--confirm", action="store_true",
                        help="Envoyer reellement les sites a l API (sans ce flag : dry-run)")
    parser.add_argument("--dossier", type=str, default=str(DEFAULT_SITES_DIR),
                        help="Dossier racine contenant les sous-dossiers de sites")
    parser.add_argument("--api", type=str, default=API_BASE)
    parser.add_argument("--email", type=str, default=DEFAULT_EMAIL)
    parser.add_argument("--password", type=str, default=DEFAULT_PASSWORD)
    parser.add_argument("--status-id", type=int, default=DEFAULT_STATUS_ID,
                        help=f"ID du statut (defaut: {DEFAULT_STATUS_ID} = Doc B depose)")
    parser.add_argument("--output-csv", type=str, default="dry_run_sites.csv")
    args = parser.parse_args()

    sites_dir = Path(args.dossier)
    mode = "IMPORT REEL" if args.confirm else "DRY-RUN (simulation)"

    print("=" * 70)
    print(f"  MZ SITEHUB - Import Doc B | Mode : {mode}")
    print(f"  Dossier : {sites_dir}")
    print(f"  API     : {args.api}")
    print(f"  Statut  : {args.status_id}")
    print("=" * 70)

    # 1. Charger les tables de reference depuis la DB
    print("\n[1/4] Chargement des tables de reference (wilayas, communes)...")
    env = load_env(_BACKEND_ENV)
    db_url = env.get("DATABASE_URL", os.environ.get("DATABASE_URL", ""))
    if not db_url:
        print("[ERREUR] DATABASE_URL non trouvee dans backend/.env")
        sys.exit(1)

    try:
        wilayas_map, communes_map = asyncio.run(load_reference_data(db_url))
        print(f"  OK : {len(wilayas_map)} wilayas | {len([k for k in communes_map if k[0] != '*'])} communes")
    except Exception as e:
        print(f"[ERREUR] Impossible de charger les references : {e}")
        sys.exit(1)

    # 2. Demarrage du backend (automatique si pas deja actif)
    print(f"\n[2/5] Verification / demarrage du backend ({args.api})...")
    backend_ok = ensure_backend_running(args.api)
    if not backend_ok:
        if args.confirm:
            print("[ERREUR] Backend non disponible - import annule.")
            sys.exit(1)
        print("  ATTENTION : backend non disponible - payloads construits mais non envoyes.")

    # 3. Authentification API
    print(f"\n[3/5] Connexion a l API ({args.api})...")
    token = None
    if backend_ok:
        token = api_login(args.email, args.password, args.api)
        if token:
            print("  OK : token obtenu")
        else:
            if args.confirm:
                stop_backend_if_started()
                print("[ERREUR] Authentification echouee - import annule")
                sys.exit(1)
            print("  ATTENTION : Login echoue - payloads construits mais non envoyes")
    else:
        print("  (ignoree : backend non disponible)")

    # 4. Scanner les dossiers et extraire les donnees
    print(f"\n[4/5] Scan des sous-dossiers...")
    site_folders = scan_sites_folder(sites_dir)
    print(f"  -> {len(site_folders)} dossier(s) avec un doc B trouve(s)\n")

    results = []
    errors = []
    payloads = []

    for folder, docb_path in site_folders:
        folder_name = folder.name
        print(f"  Traitement : {folder_name}")
        print(f"    Fichier  : {docb_path.name}")

        try:
            data = parse_docb(docb_path)
        except Exception as e:
            msg = f"Erreur lecture Excel : {e}"
            print(f"    ECHEC : {msg}")
            errors.append({"dossier": folder_name, "fichier": docb_path.name, "erreur": msg})
            continue

        # Resolution wilaya_id
        wilaya_id = None
        wilaya_warn = ""
        if data["wilaya_raw"]:
            key = normalize(data["wilaya_raw"])
            wilaya_id = wilayas_map.get(key)
            if wilaya_id is None:
                # Match partiel
                matches = [(k, v) for k, v in wilayas_map.items() if key in k or k in key]
                if len(matches) == 1:
                    wilaya_id = matches[0][1]
                    wilaya_warn = f"match partiel '{matches[0][0]}'"
                else:
                    wilaya_warn = f"WARN: wilaya '{data['wilaya_raw']}' non reconnue"

        # Resolution commune_id
        commune_id = None
        commune_warn = ""
        if data["commune_raw"]:
            key = normalize(data["commune_raw"])
            if wilaya_id:
                commune_id = communes_map.get((wilaya_id, key))
            if commune_id is None:
                commune_id = communes_map.get(("*", key))
            if commune_id is None:
                commune_warn = f"WARN: commune '{data['commune_raw']}' non reconnue"

        # Verifications
        issues = []
        if not data["code"]:
            issues.append("Code site manquant (cellule A5 vide)")
        if wilaya_warn:
            issues.append(wilaya_warn)
        if commune_warn:
            issues.append(commune_warn)
        if data["latitude"] is None:
            issues.append("GPS non parseable")

        status_icon = "WARN" if issues else "OK"
        print(f"    {status_icon} : Code={data['code']} | Wilaya={data['wilaya_raw']}(id={wilaya_id}) | Commune={data['commune_raw']}(id={commune_id})")
        if data["latitude"]:
            print(f"       GPS : lat={data['latitude']}, lon={data['longitude']}")
        for iss in issues:
            print(f"       ! {iss}")

        # Payload SiteCreate
        payload = {
            "code":         data["code"] or f"INCONNU_{folder_name[:10]}",
            "name":         data["name"],
            "wilaya_id":    wilaya_id,
            "commune_id":   commune_id,
            "address":      data["address"],
            "latitude":     data["latitude"],
            "longitude":    data["longitude"],
            "site_type":    data["site_type"],
            "owner_name":   data["owner_name"],
            "organisme":    data["organisme"],
            "status_id":    args.status_id,
            "priority":     2,
            "is_favorite":  False,
            "custom_fields": data["custom_fields"],
        }
        # Retirer les None (sauf status_id et code qui sont requis)
        payload_clean = {k: v for k, v in payload.items()
                         if v is not None or k in ("status_id", "code")}

        results.append({
            "dossier":      folder_name,
            "fichier_docb": docb_path.name,
            "code":         data["code"],
            "nom":          data["name"],
            "wilaya_raw":   data["wilaya_raw"],
            "wilaya_id":    wilaya_id,
            "commune_raw":  data["commune_raw"],
            "commune_id":   commune_id,
            "latitude":     data["latitude"],
            "longitude":    data["longitude"],
            "site_type":    data["site_type"],
            "organisme":    data["organisme"],
            "proprietaire": data["owner_name"],
            "gps_lon_brut": data["custom_fields"].get("gps_brut_longitude", ""),
            "gps_lat_brut": data["custom_fields"].get("gps_brut_latitude", ""),
            "type_propriete": data["custom_fields"].get("type_propriete", ""),
            "sonelgaz":     data["custom_fields"].get("connexion_sonelgaz", ""),
            "issues":       " | ".join(issues),
            "action":       "SKIP_NO_CODE" if not data["code"] else ("WARN" if issues else "OK"),
        })
        payloads.append((folder_name, payload_clean, issues, data["code"]))

    # 5. Export CSV dry-run
    csv_path = Path(args.output_csv)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    print(f"\n[5/5] Recapitulatif dry-run exporte : {csv_path.absolute()}")
    print(f"\n{'='*60}")
    print(f"  Dossiers traites    : {len(site_folders)}")
    print(f"  Sites OK            : {sum(1 for r in results if r['action']=='OK')}")
    print(f"  Sites avec warnings : {sum(1 for r in results if r['action']=='WARN')}")
    print(f"  Sites sans code     : {sum(1 for r in results if r['action']=='SKIP_NO_CODE')}")
    print(f"  Erreurs lecture     : {len(errors)}")
    print(f"{'='*60}")

    if not args.confirm:
        print("\n  Mode DRY-RUN - aucun site n a ete cree dans la base.")
        print("  Verifiez le CSV, puis relancez avec --confirm pour importer.\n")
        stop_backend_if_started()
        return

    # === IMPORT REEL ===
    if not token:
        print("[ERREUR] Token manquant - verifiez que le backend est demarre.")
        sys.exit(1)

    print(f"\n IMPORT REEL - envoi de {len(payloads)} sites...")
    success_count = 0
    fail_count = 0
    fail_details = []

    for folder_name, payload_clean, issues, code in payloads:
        if not code or code.startswith("INCONNU_"):
            msg = "Code site manquant - non envoye"
            print(f"  SKIP [{folder_name}]: {msg}")
            fail_count += 1
            fail_details.append({"dossier": folder_name, "code": code, "raison": msg})
            continue

        ok, msg = api_create_site(payload_clean, token, args.api)
        if ok:
            print(f"  OK [{code}] ({folder_name}): {msg}")
            success_count += 1
        else:
            print(f"  ECHEC [{code}] ({folder_name}): {msg}")
            fail_count += 1
            fail_details.append({"dossier": folder_name, "code": code, "raison": msg})

    print(f"\n{'='*60}")
    print(f"  Reussis  : {success_count}")
    print(f"  Echecs   : {fail_count}")
    if fail_details:
        print("\n  Detail des echecs :")
        for fd in fail_details:
            print(f"    [{fd['code']}] {fd['dossier']}: {fd['raison']}")
    print(f"{'='*60}\n")
    stop_backend_if_started()


if __name__ == "__main__":
    main()

