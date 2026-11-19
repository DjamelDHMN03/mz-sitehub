import os, csv
from datetime import datetime, date
from collections import Counter
from openpyxl import load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "SUIVI_NETTOYE.xlsx")
REPORT = os.path.join(HERE, "rapport_import_suivi.csv")
LON_RANGE = (-9.0, 12.5)
LAT_RANGE = (18.5, 38.0)
DEFAULT_STATUS_ID = 1

# ATTENTION : ids 1 a 4 confirmes, ids 5 a 22 a verifier dans la table site_status
STATUS_MAP = {
    "NOUVEAU": 1,
    "RECHERCHE_TERRAIN": 2,
    "PROPOSITION": 3,
    "DOCB_A_PREPARER": 4,
    "ATTENTE CCT": 5,
    "ATTENTE DOC B": 6,
    "ATTENTE TSS": 7,
    "ATTENTE SIGNATURE CONTRAT": 8,
    "BLOQUE": 9,
    "BOUCLEE": 10,
    "CCT DEFAVORABLE": 11,
    "AVIS DEFAVORABLE": 12,
    "ATTENTE ENQUETTE FONCIERE": 13,
    "ATTENTE RETOUR OPGI": 14,
    "VISITE REPORTEE": 15,
    "ATTENTE AUTORISATION DJS": 16,
    "ATTENTE RETOUR RAIL TELECOM": 16,
    "ATTENTE AUTORISATION": 16,
    "ATTENTE DOSSIER EXPERT GEOMETRE POUR DEPOT.": 17,
    "ATTENTE AUTORISATION DE CONSTRUIRE": 16,
    "PAS DE CANDIDATS": 18,
    "PAS DE CANDIDAT": 18,
    "ATTENTE RETOUR DOMAINES": 14,
    "PREACQUIS": 19,
    "ATTENTE RETOUR DW ET DRAG": 14,
    "PREACQUIS ATTENTE AUTORISATION AADL": 19,
    "ECHEC OPPOSITION": 20,
    "ECHEC ACQUISITION": 20,
    "ATTENTE COFIRMATION NUMILOG": 14,
    "ATTENTE DEMANDE APC": 16,
    "ATTENTE KO": 21,
    "ATTENTE APS": 22,
    "ATTENTE RETOUR DIRECTION DES MOUDJAHIDINES": 14,
}


def clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def to_float(v):
    v = clean(v)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def coords(r, warnings):
    pairs = [("GPS LONG", "GPS LAT"), ("GPS LONG POINT NOMINAL", "GPS LAT POINT NOMINAL")]
    for lon_k, lat_k in pairs:
        lon, lat = to_float(r.get(lon_k)), to_float(r.get(lat_k))
        if lon is None or lat is None:
            continue
        if LON_RANGE[0] <= lon <= LON_RANGE[1] and LAT_RANGE[0] <= lat <= LAT_RANGE[1]:
            return lon, lat
        warnings.append("coordonnees hors Algerie (%s, %s) ignorees" % (lon, lat))
    return None, None


def main():
    wb = load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb["Sites"]
    it = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(it)]
    sites, skipped, seen = [], [], set()
    for idx, vals in enumerate(it, start=2):
        if all(clean(v) is None for v in vals):
            continue
        r = dict(zip(headers, vals))
        code = clean(r.get("Code Site"))
        if not code:
            skipped.append((idx, "", "code site vide"))
            continue
        code = str(code)
        if code in seen:
            skipped.append((idx, code, "doublon de code"))
            continue
        seen.add(code)
        warnings = []
        lon, lat = coords(r, warnings)
        av = clean(r.get("AVANCEMENT"))
        key = str(av).strip().upper() if av else ""
        mappe = key in STATUS_MAP
        sites.append({
            "ligne": idx, "code": code,
            "nom": clean(r.get("Nom Candidat")) or clean(r.get("Adresse")) or code,
            "wilaya": clean(r.get("WILAYA")), "commune": clean(r.get("COMMUNE")),
            "lat": lat, "lon": lon,
            "avancement": av, "status_id": STATUS_MAP.get(key, DEFAULT_STATUS_ID),
            "mappe": mappe,
            "doc_b": to_date(r.get("DOC B Date")),
            "alertes": " | ".join(warnings),
        })

    with open(REPORT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ligne", "code", "nom", "wilaya", "commune", "lat", "lon",
                    "avancement", "status_id", "statut_mappe", "doc_b_date", "alertes"])
        for s in sites:
            w.writerow([s["ligne"], s["code"], s["nom"], s["wilaya"], s["commune"],
                        s["lat"], s["lon"], s["avancement"], s["status_id"],
                        "oui" if s["mappe"] else "NON", s["doc_b"], s["alertes"]])

    print("Sites lus              :", len(sites))
    print("Lignes ignorees        :", len(skipped))
    for ligne, code, why in skipped:
        print("   ligne", ligne, code, "->", why)
    print("Sans coordonnees       :", sum(1 for s in sites if s["lon"] is None))
    print("Avec DOC B Date        :", sum(1 for s in sites if s["doc_b"]))
    print("Avec alertes           :", sum(1 for s in sites if s["alertes"]))
    print("")
    print("Statuts AVANCEMENT non mappes (statut %d par defaut) :" % DEFAULT_STATUS_ID)
    non = Counter(s["avancement"] or "(vide)" for s in sites if not s["mappe"])
    if non:
        for k, n in non.most_common():
            print("  %3d  %s" % (n, k))
    else:
        print("  aucun")
    print("")
    print("Rapport ecrit :", REPORT)
    print("MODE SIMULATION : rien n'a ete ecrit en base.")


main()