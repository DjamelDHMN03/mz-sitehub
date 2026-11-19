#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import des fichiers "doc B" (Excel) vers la base MZ Sitehub (Supabase/PostgreSQL).

Ce script :
  1. Parcourt un dossier racine (ex: "New Sites") et trouve tous les fichiers
     nommés docb_*.xlsx, où qu'ils soient dans l'arborescence.
  2. Extrait les champs connus (site, wilaya, commune, coordonnées GPS, etc.)
  3. Retrouve wilaya_id / commune_id en base à partir des noms texte.
  4. Par défaut (DRY-RUN) : affiche seulement ce qui SERAIT fait, sans rien écrire.
  5. Avec --commit : écrit réellement en base :
       - crée le site s'il n'existe pas (par code), sinon met à jour les
         champs extraits sans écraser ceux qui existent déjà et que le
         fichier ne fournit pas.
       - crée une ligne doc_b liée à ce site (reference = code du site,
         organisme = société, status = 'Déposé', date_preparation = date
         de visite, date_depot = NULL).

Utilisation :
    python import_docb.py "C:\\Users\\WINDOWS 11\\OneDrive\\Desktop\\New Sites"
    python import_docb.py "C:\\...\\New Sites" --commit
    python import_docb.py "C:\\...\\New Sites" --commit --status PROPOSITION

Prérequis (une seule fois) :
    pip install openpyxl psycopg2-binary python-dotenv --break-system-packages

Le script lit DATABASE_URL depuis le fichier .env du dossier backend
(passé avec --env, par défaut il cherche ".env" dans le dossier courant).
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

# Force l'UTF-8 en sortie pour éviter les erreurs d'encodage sur Windows
# (notamment lors d'une redirection ">" vers un fichier en PowerShell).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

try:
    import openpyxl
except ImportError:
    sys.exit("Il manque 'openpyxl'. Lance : pip install openpyxl --break-system-packages")

# psycopg2 n'est nécessaire qu'en mode --commit (écriture en base).
# Import différé pour que le mode dry-run fonctionne sans ce paquet installé.
psycopg2 = None


# --------------------------------------------------------------------------- #
# 1. Lecture de la configuration (.env)
# --------------------------------------------------------------------------- #

def load_database_url(env_path: Path) -> str:
    if not env_path.exists():
        sys.exit(f"Fichier .env introuvable : {env_path}")
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            # psycopg2 ne comprend pas le driver "+asyncpg" utilisé par SQLAlchemy
            url = url.replace("postgresql+asyncpg://", "postgresql://")
            return url
    sys.exit(f"DATABASE_URL introuvable dans {env_path}")


# --------------------------------------------------------------------------- #
# 2. Extraction d'un fichier doc B (mise en page connue, feuille "Feuil1")
# --------------------------------------------------------------------------- #

CELL_MAP = {
    "code": "A5",
    "candidat": "F5",
    "name": "H5",
    "region": "B9",
    "negociateur": "H9",
    "wilaya": "B10",
    "portable": "H10",
    "daira": "B11",
    "organisme": "H11",
    "commune": "B12",
    "date_visite_raw": "H12",
    "address": "A17",
    "longitude_raw": "K25",
    "latitude_raw": "K26",
    "site_type": "A47",
    "environnement": "A50",
    "securite_zone": "A53",
}


def parse_date_fr(raw):
    """Parse une date au format observé 'JJ MM AAAA' (séparée par espaces)."""
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    s = str(raw).strip()
    m = re.match(r"(\d{1,2})\s+(\d{1,2})\s+(\d{4})", s)
    if m:
        d, mo, y = map(int, m.groups())
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def parse_float(raw):
    """Parse une coordonnée GPS, qu'elle soit en décimal simple (avec
    éventuelle virgule parasite en début/fin) ou au format DMS
    (ex: 2°54'33.38"E)."""
    if raw is None:
        return None
    s = str(raw).strip()
    s = s.strip(",").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    m = re.match(r"(\d+)\D+(\d+)\D+([\d.]+)\D*([NSEWnsew])?", s)
    if m:
        deg, minute, sec, hemi = m.groups()
        value = float(deg) + float(minute) / 60 + float(sec) / 3600
        if hemi and hemi.upper() in ("S", "W"):
            value = -value
        return value
    return None


# Bornes géographiques larges de l'Algérie, utilisées comme garde-fou :
# toute coordonnée calculée en dehors de cette zone est très probablement
# le résultat d'un parsing incorrect (format inattendu dans la cellule) et
# est rejetée plutôt qu'insérée telle quelle.
ALGERIA_LON_RANGE = (-9.0, 12.5)
ALGERIA_LAT_RANGE = (18.5, 38.0)


def sanity_check_coords(lon, lat, raw_lon, raw_lat):
    """Retourne (lon, lat, warning_ou_None). Rejette (met à None) toute
    coordonnée hors des bornes plausibles pour l'Algérie."""
    warning = None
    if lon is not None and not (ALGERIA_LON_RANGE[0] <= lon <= ALGERIA_LON_RANGE[1]):
        warning = (f"longitude aberrante rejetée : {lon} "
                   f"(valeur brute dans le fichier : {raw_lon!r})")
        lon = None
    if lat is not None and not (ALGERIA_LAT_RANGE[0] <= lat <= ALGERIA_LAT_RANGE[1]):
        w2 = (f"latitude aberrante rejetée : {lat} "
              f"(valeur brute dans le fichier : {raw_lat!r})")
        warning = f"{warning}; {w2}" if warning else w2
        lat = None
    return lon, lat, warning


def clean_str(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return str(v).strip() or None


def extract_docb(path: Path) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    if "Feuil1" not in wb.sheetnames:
        raise ValueError(f"Feuille 'Feuil1' introuvable dans {path.name}")
    ws = wb["Feuil1"]

    raw = {key: ws[coord].value for key, coord in CELL_MAP.items()}

    base_code = clean_str(raw["code"])
    candidat = clean_str(raw["candidat"])
    # Chaque proposition (candidat A, B, C...) pour un même site physique
    # devient un site distinct en base, identifié par "<Site ID>-<Candidat>".
    # S'il n'y a pas de candidat renseigné, on garde le code tel quel.
    site_code = f"{base_code}-{candidat}" if (base_code and candidat) else base_code

    lon = parse_float(raw["longitude_raw"])
    lat = parse_float(raw["latitude_raw"])
    lon, lat, gps_warning = sanity_check_coords(
        lon, lat, raw["longitude_raw"], raw["latitude_raw"]
    )

    data = {
        "code": site_code,
        "base_site_id": base_code,
        "candidat": candidat,
        "name": clean_str(raw["name"]),
        "region": clean_str(raw["region"]),
        "negociateur": clean_str(raw["negociateur"]),
        "wilaya": clean_str(raw["wilaya"]),
        "portable": clean_str(raw["portable"]),
        "daira": clean_str(raw["daira"]),
        "organisme": clean_str(raw["organisme"]),
        "commune": clean_str(raw["commune"]),
        "date_visite": parse_date_fr(raw["date_visite_raw"]),
        "address": clean_str(raw["address"]),
        "longitude": lon,
        "latitude": lat,
        "_gps_warning": gps_warning,
        "site_type": clean_str(raw["site_type"]),
        "environnement": clean_str(raw["environnement"]),
        "securite_zone": clean_str(raw["securite_zone"]),
        "_source_file": str(path),
    }
    return data


def find_docb_files(root: Path):
    pattern = re.compile(r"^docb.*\.xlsx$", re.IGNORECASE)
    for p in root.rglob("*.xlsx"):
        if pattern.match(p.name) and not p.name.startswith("~$"):
            yield p


PLACEHOLDER_RE = re.compile(r"x{3,}", re.IGNORECASE)


def is_placeholder_code(code):
    """Détecte les codes provisoires du type AL_XXXX, Alxxxx (pas encore
    attribués par le Geomarketing)."""
    return bool(code) and bool(PLACEHOLDER_RE.search(code))


def slug_from_path(path: Path, root: Path) -> str:
    """Construit un identifiant lisible et unique à partir du chemin du
    fichier (dossiers parents), utilisé pour fabriquer un code provisoire."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts = list(rel.parts[:-1])  # tous les dossiers, sans le nom du fichier
    slug = "-".join(parts)
    slug = re.sub(r"[^A-Za-z0-9\-]+", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or path.stem


def resolve_site_code(data: dict, path: Path, root: Path) -> dict:
    """Remplace le code par un code provisoire unique si le Site ID est un
    placeholder (contient XXXX). Ajoute un flag _provisional pour le rapport."""
    data["_provisional"] = False
    if is_placeholder_code(data["base_site_id"]):
        slug = slug_from_path(path, root)
        provisional_base = f"{data['base_site_id']}-PROV-{slug}"
        data["code"] = (f"{provisional_base}-{data['candidat']}"
                         if data["candidat"] else provisional_base)
        # Le champ "code" a une limite de 32 caractères côté base
        data["code"] = data["code"][:32]
        data["_provisional"] = True
    return data


def folder_wilaya_name(path: Path, root: Path):
    """Le premier dossier sous la racine (ex: 'New Sites/DJELFA/...') donne
    la wilaya selon le classement de l'utilisateur — plus fiable que le
    texte libre tapé dans la cellule Excel."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return None
    if len(rel.parts) < 2:
        return None
    return rel.parts[0].strip()


def resolve_wilaya(data: dict, path: Path, root: Path) -> dict:
    """Fait confiance au classement par dossier plutôt qu'à la cellule Excel
    quand les deux diffèrent (saisie manuelle plus sujette aux erreurs)."""
    data["_wilaya_override"] = None
    folder_name = folder_wilaya_name(path, root)
    if not folder_name:
        return data
    cell_wilaya = (data["wilaya"] or "").strip().upper()
    folder_wilaya = folder_name.strip().upper()
    if cell_wilaya and cell_wilaya != folder_wilaya:
        data["_wilaya_override"] = (data["wilaya"], folder_name)
        data["wilaya"] = folder_name
    elif not cell_wilaya:
        data["wilaya"] = folder_name
    return data


# --------------------------------------------------------------------------- #
# 3. Base de données : lookups + upsert
# --------------------------------------------------------------------------- #

class DbHelper:
    def __init__(self, conn):
        self.conn = conn
        self._wilaya_cache = {}
        self._commune_cache = {}

    def wilaya_id(self, name):
        if not name:
            return None
        key = name.strip().upper()
        if key in self._wilaya_cache:
            return self._wilaya_cache[key]
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM wilayas WHERE upper(trim(name)) = %s LIMIT 1", (key,))
            row = cur.fetchone()
            result = row[0] if row else None
            self._wilaya_cache[key] = result
            return result

    def commune_id(self, name, wilaya_id):
        if not name or not wilaya_id:
            return None
        key = (name.strip().upper(), wilaya_id)
        if key in self._commune_cache:
            return self._commune_cache[key]
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM communes WHERE upper(trim(name)) = %s AND wilaya_id = %s LIMIT 1",
                (key[0], wilaya_id),
            )
            row = cur.fetchone()
            result = row[0] if row else None
            self._commune_cache[key] = result
            return result

    def status_id(self, code):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM site_status WHERE code = %s LIMIT 1", (code,))
            row = cur.fetchone()
            return row[0] if row else None

    def find_site_by_code(self, code):
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM sites WHERE code = %s LIMIT 1", (code,))
            return cur.fetchone()

    def upsert_site(self, data, status_id):
        existing = self.find_site_by_code(data["code"])
        wid = self.wilaya_id(data["wilaya"])
        cid = self.commune_id(data["commune"], wid)

        geom_sql = None
        params_geom = []
        if data["longitude"] is not None and data["latitude"] is not None:
            geom_sql = "ST_SetSRID(ST_MakePoint(%s, %s), 4326)"
            params_geom = [data["longitude"], data["latitude"]]

        if existing is None:
            cols = ["code", "name", "wilaya_id", "commune_id", "address",
                    "site_type", "owner_name", "organisme", "status_id"]
            vals = [data["code"], data["name"], wid, cid, data["address"],
                    data["site_type"], None, data["organisme"], status_id]
            placeholders = ["%s"] * len(vals)
            if geom_sql:
                cols.append("geom")
                placeholders.append(geom_sql)
                vals.extend(params_geom)
            sql = f"""
                INSERT INTO sites ({', '.join(cols)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """
            with self.conn.cursor() as cur:
                cur.execute(sql, vals)
                return cur.fetchone()[0], "created"
        else:
            # Met à jour uniquement les champs extraits et non vides,
            # sans écraser un champ déjà rempli par autre chose que NULL
            # si le fichier ne fournit rien.
            updates = []
            vals = []
            field_map = {
                "name": data["name"],
                "wilaya_id": wid,
                "commune_id": cid,
                "address": data["address"],
                "site_type": data["site_type"],
                "organisme": data["organisme"],
            }
            for col, val in field_map.items():
                if val is not None:
                    updates.append(f"{col} = %s")
                    vals.append(val)
            if geom_sql:
                updates.append(f"geom = {geom_sql}")
                vals.extend(params_geom)
            updates.append("updated_at = now()")
            if updates:
                sql = f"UPDATE sites SET {', '.join(updates)} WHERE id = %s"
                vals.append(existing["id"])
                with self.conn.cursor() as cur:
                    cur.execute(sql, vals)
            return existing["id"], "updated"

    def upsert_docb(self, site_id, data, docb_status_label):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM doc_b WHERE site_id = %s LIMIT 1", (site_id,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE doc_b
                    SET reference = %s, organisme = %s, status = %s,
                        date_preparation = %s, date_depot = NULL
                    WHERE id = %s
                    """,
                    (data["code"], data["organisme"], docb_status_label,
                     data["date_visite"], row[0]),
                )
                return "updated"
            else:
                cur.execute(
                    """
                    INSERT INTO doc_b (site_id, reference, organisme, status,
                                        date_preparation, date_depot)
                    VALUES (%s, %s, %s, %s, %s, NULL)
                    """,
                    (site_id, data["code"], data["organisme"], docb_status_label,
                     data["date_visite"]),
                )
                return "created"


# --------------------------------------------------------------------------- #
# 4. Programme principal
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="Import des doc B vers MZ Sitehub")
    parser.add_argument("root", help="Dossier racine à parcourir (ex: 'New Sites')")
    parser.add_argument("--env", default=".env", help="Chemin vers le fichier .env du backend")
    parser.add_argument("--commit", action="store_true",
                         help="Écrit réellement en base (sinon: dry-run, rien n'est écrit)")
    parser.add_argument("--status", default="PROPOSITION",
                         help="Code du statut à assigner aux sites créés (défaut: PROPOSITION)")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        sys.exit(f"Dossier introuvable : {root}")

    files = list(find_docb_files(root))
    print(f"{len(files)} fichier(s) doc B trouvé(s) sous {root}\n")

    if not files:
        print("Rien à faire.")
        return

    extracted = []
    for f in files:
        try:
            d = extract_docb(f)
            if not d["code"]:
                print(f"  [IGNORÉ] {f.name} : pas de Site ID trouvé (cellule A5 vide)")
                continue
            d = resolve_site_code(d, f, root)
            d = resolve_wilaya(d, f, root)
            extracted.append(d)
        except Exception as e:
            print(f"  [ERREUR] {f.name} : {e}")

    print(f"\n{len(extracted)} fichier(s) exploitable(s).\n")

    provisional = [d for d in extracted if d["_provisional"]]
    if provisional:
        print(f"[ATTENTION] {len(provisional)} site(s) sans code officiel (Geomarketing) — "
              f"code provisoire généré, à renommer une fois le vrai code connu :")
        for d in provisional:
            print(f"    {d['_source_file']}\n      -> code provisoire : {d['code']}")
        print()

    # Détection des collisions : plusieurs fichiers différents qui aboutiraient
    # au même code (typiquement : plusieurs candidats sans lettre A/B/C pour
    # distinguer les propositions). Sans cette étape, le deuxième écraserait
    # silencieusement le premier en base.
    by_code = {}
    for d in extracted:
        by_code.setdefault(d["code"], []).append(d)
    collisions = {code: items for code, items in by_code.items() if len(items) > 1}
    if collisions:
        print(f"[ATTENTION] {len(collisions)} code(s) en collision (plusieurs fichiers, "
              f"pas de lettre candidat pour les distinguer) — un suffixe -DUPn a été "
              f"ajouté automatiquement, à corriger à la source si possible :")
        for code, items in collisions.items():
            for i, d in enumerate(items, start=1):
                old_code = d["code"]
                d["code"] = f"{old_code}-DUP{i}"
                d["_provisional"] = True
                print(f"    {d['_source_file']}\n      -> {old_code} devient {d['code']}")
        print()

    gps_warnings = [d for d in extracted if d["_gps_warning"]]
    if gps_warnings:
        print(f"[ATTENTION] {len(gps_warnings)} coordonnée(s) GPS aberrante(s) rejetée(s) "
              f"(hors des limites de l'Algérie) — à vérifier et corriger dans le fichier source :")
        for d in gps_warnings:
            print(f"    {d['code']} ({d['_source_file']})\n      -> {d['_gps_warning']}")
        print()

    wilaya_overrides = [d for d in extracted if d["_wilaya_override"]]
    if wilaya_overrides:
        print(f"[ATTENTION] {len(wilaya_overrides)} wilaya corrigée(s) d'après le dossier "
              f"(différait du texte de la cellule Excel) :")
        for d in wilaya_overrides:
            old, new = d["_wilaya_override"]
            print(f"    {d['code']} : cellule={old!r} -> dossier={new!r} (dossier utilisé)")
        print()

    if not args.commit:
        print("=== MODE DRY-RUN (rien n'est écrit en base) ===\n")
        for d in extracted:
            flag = " [PROVISOIRE]" if d["_provisional"] else ""
            print(f"- {d['code']:14} (site {d['base_site_id']}, prop. {d['candidat']}){flag} | "
                  f"{d['name'] or '(sans nom)':25} | "
                  f"wilaya={d['wilaya']!r:15} commune={d['commune']!r:15} | "
                  f"GPS=({d['longitude']}, {d['latitude']}) | visite={d['date_visite']}")
        print("\nRelance avec --commit pour écrire réellement ces données en base.")
        return

    global psycopg2
    try:
        import psycopg2 as _psycopg2
        import psycopg2.extras  # noqa: F401
        psycopg2 = _psycopg2
    except ImportError:
        sys.exit("Il manque 'psycopg2'. Lance : pip install psycopg2-binary --break-system-packages")

    db_url = load_database_url(Path(args.env))
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    helper = DbHelper(conn)

    status_id = helper.status_id(args.status)
    if status_id is None:
        conn.close()
        sys.exit(f"Statut '{args.status}' introuvable dans site_status. Vérifie le code exact.")

    summary = {"sites_created": 0, "sites_updated": 0,
               "docb_created": 0, "docb_updated": 0, "warnings": []}

    try:
        for d in extracted:
            site_id, site_action = helper.upsert_site(d, status_id)
            if site_action == "created":
                summary["sites_created"] += 1
            else:
                summary["sites_updated"] += 1

            if d["_provisional"]:
                summary["warnings"].append(
                    f"{d['code']}: code PROVISOIRE (Site ID d'origine '{d['base_site_id']}' "
                    f"pas encore attribué par le Geomarketing) — à renommer plus tard"
                )
            if d["_wilaya_override"]:
                old, new = d["_wilaya_override"]
                summary["warnings"].append(
                    f"{d['code']}: wilaya corrigée d'après le dossier ({old!r} -> {new!r})"
                )
            if d["_gps_warning"]:
                summary["warnings"].append(f"{d['code']}: {d['_gps_warning']}")
            if not helper.wilaya_id(d["wilaya"]):
                summary["warnings"].append(f"{d['code']}: wilaya '{d['wilaya']}' introuvable en base")
            elif not helper.commune_id(d["commune"], helper.wilaya_id(d["wilaya"])):
                summary["warnings"].append(f"{d['code']}: commune '{d['commune']}' introuvable en base")

            docb_action = helper.upsert_docb(site_id, d, "Déposé")
            if docb_action == "created":
                summary["docb_created"] += 1
            else:
                summary["docb_updated"] += 1

            print(f"OK  {d['code']:10} -> site {site_action}, doc_b {docb_action}")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n=== RÉSUMÉ ===")
    print(f"Sites créés   : {summary['sites_created']}")
    print(f"Sites mis à jour : {summary['sites_updated']}")
    print(f"Doc B créés   : {summary['docb_created']}")
    print(f"Doc B mis à jour : {summary['docb_updated']}")
    if summary["warnings"]:
        print(f"\n{len(summary['warnings'])} avertissement(s) :")
        for w in summary["warnings"]:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
