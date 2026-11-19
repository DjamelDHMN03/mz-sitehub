"""
Génère un fichier Excel au format d'import natif de MZ Sitehub
(colonnes : Code Site, Statut, Commune, Adresse, Latitude, Longitude, Google Maps)
à partir de tous les fichiers "doc B" trouvés dans le dossier New Sites.

AUCUN accès à l'API ou au backend n'est nécessaire pour ce script :
il lit juste les Excel sources et écrit un Excel de sortie.
Tu importes ensuite ce fichier de sortie toi-même via le bouton
"Importer Excel" de l'application.

UTILISATION :
1. Modifie SITES_ROOT et OUTPUT_PATH ci-dessous si besoin.
2. Lance :
     python generate_import_excel.py
3. Ouvre le fichier généré (sites_import_genere.xlsx) et vérifie-le.
4. Va dans MZ Sitehub > Sites > Importer Excel, et glisse-dépose ce fichier.

Nécessite : pip install openpyxl
"""

import re
import sys
from pathlib import Path

import openpyxl
from openpyxl import Workbook

# ============ À MODIFIER SI BESOIN ============
SITES_ROOT = r"C:\Users\WINDOWS 11\OneDrive\Desktop\New Sites"
OUTPUT_PATH = "sites_import_genere.xlsx"
DEFAULT_STATUT = "NOUVEAU"
# ================================================


CELL_MAP = {
    "site_id": "A5",
    "nom_site": "H5",
    "commune": "B12",
    "adresse": "A17",
    "longitude": "K25",
    "latitude": "K26",
}


def parse_coord(value):
    """
    Convertit une coordonnée GPS en décimal, qu'elle soit déjà décimale
    (float ou string "3.09623") ou au format degrés/minutes/secondes
    (string "3°11'51.4\"E" ou "36°39'35.27\"N").
    Retourne None si la valeur est vide ou illisible.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return None

    # Certaines cellules contiennent du texte parasite après la vraie valeur
    # (ex: "3.152792\n\nX\n\n92" à cause d'une fusion de cellules qui déborde).
    # On ne garde que la première ligne / le premier "mot" utile.
    first_chunk = s.split("\n")[0].strip()
    if first_chunk:
        s = first_chunk

    # Essaie d'abord un simple float (avec virgule ou point)
    try:
        return float(s.replace(",", "."))
    except ValueError:
        pass

    # Si ça ne marche toujours pas, cherche le premier nombre décimal
    # présent n'importe où dans la chaîne d'origine (filet de sécurité)
    num_match = re.search(r"-?\d+[.,]\d+", s)
    if num_match:
        try:
            return float(num_match.group(0).replace(",", "."))
        except ValueError:
            pass

    # Format DMS : ex 3°11'51.4"E  ou  36°39'35.27"N
    match = re.match(
        r"""(?P<deg>\d+(?:[.,]\d+)?)\s*°\s*
            (?:(?P<min>\d+(?:[.,]\d+)?)\s*['\u2019]\s*)?
            (?:(?P<sec>\d+(?:[.,]\d+)?)\s*["\u201d]?\s*)?
            (?P<dir>[NSEO])?""",
        s,
        re.VERBOSE,
    )
    if match:
        deg = float(match.group("deg").replace(",", "."))
        minutes = float(match.group("min").replace(",", ".")) if match.group("min") else 0
        seconds = float(match.group("sec").replace(",", ".")) if match.group("sec") else 0
        decimal = deg + minutes / 60 + seconds / 3600
        direction = match.group("dir")
        if direction in ("S", "O", "W"):
            decimal = -decimal
        return round(decimal, 8)

    return None


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
    Parcourt New Sites/<région>/<dossier de site>/ et cherche TOUS les
    fichiers doc B en dessous, à n'importe quelle profondeur (certains
    sites ont un niveau supplémentaire de sous-dossiers "candidats" A/B).
    Retourne une liste de tuples (nom_region, nom_dossier_site, chemin_xlsx).
    S'il y a plusieurs doc B sous un même dossier de site (plusieurs
    candidats), CHACUN est retourné -- ça peut faire apparaître des codes
    en double dans l'aperçu si les deux candidats partagent le même
    Site ID, ce qui est normal et à trancher manuellement.
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
                list(site_folder.rglob("docb_*.xlsx"))
                + list(site_folder.rglob("DOCB_*.xlsx"))
                + list(site_folder.rglob("DocB_*.xlsx"))
                + list(site_folder.rglob("Docb_*.xlsx"))
            )
            # dédoublonne au cas où plusieurs motifs matchent le même fichier
            matches = list(dict.fromkeys(matches))
            if matches:
                for m in matches:
                    results.append((region_folder.name, site_folder.name, m))
            else:
                print(f"[!] Pas de doc B trouvé dans : {region_folder.name} / {site_folder.name}")
    return results


def main():
    site_files = find_doc_b_files(SITES_ROOT)
    print(f"[INFO] {len(site_files)} dossier(s) de site avec doc B trouvé(s)\n")

    out_wb = Workbook()
    out_ws = out_wb.active
    out_ws.title = "Sites"
    out_ws.append(["Code Site", "Statut", "Commune", "Adresse", "Latitude", "Longitude", "Google Maps"])

    seen_codes = set()
    n_ok, n_issues = 0, 0

    for region_name, site_folder_name, xlsx_path in site_files:
        label = f"{region_name} / {site_folder_name} / {xlsx_path.stem}"
        try:
            doc_data = read_doc_b(xlsx_path)
        except Exception as e:
            print(f"[X] Erreur lecture {label} : {e}")
            n_issues += 1
            continue

        code = str(doc_data.get("site_id") or "").strip()
        commune = str(doc_data.get("commune") or "").strip()
        adresse = str(doc_data.get("adresse") or "").strip()
        lat = parse_coord(doc_data.get("latitude"))
        lon = parse_coord(doc_data.get("longitude"))

        problems = []
        if not code:
            problems.append("code manquant")
        elif code in seen_codes:
            problems.append("code en double")
        if not commune:
            problems.append("commune manquante")
        if lat is None:
            problems.append("latitude illisible")
        if lon is None:
            problems.append("longitude illisible")

        if problems:
            print(f"[!] {label} -> {', '.join(problems)} (code brut: {code!r})")
            n_issues += 1
            continue

        seen_codes.add(code)
        gmaps = f"https://www.google.com/maps?q={lat},{lon}"
        out_ws.append([code, DEFAULT_STATUT, commune, adresse, lat, lon, gmaps])
        n_ok += 1

    out_wb.save(OUTPUT_PATH)
    print(f"\n[OK] {n_ok} site(s) écrits dans {OUTPUT_PATH}")
    print(f"[!] {n_issues} site(s) ignorés (voir messages ci-dessus)")
    print("\nOuvre le fichier généré pour vérifier avant de l'importer dans MZ Sitehub.")


if __name__ == "__main__":
    main()
