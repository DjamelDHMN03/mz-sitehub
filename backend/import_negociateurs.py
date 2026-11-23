#!/usr/bin/env python3
"""
import_negociateurs.py
----------------------
Lit le fichier de suivi (Excel .xlsx, ou texte .csv/.tsv/.txt copie-colle) et :
  1. attribue chaque site a son negociateur (colonne "Charge Acquisition")
  2. enrichit la fiche du site (wilaya si vide + champs personnalises :
     projet, typo_site, delai_doc_b, avancement, categorie)
  3. (option) cree les sites qui n'existent pas encore

Par defaut : DRY-RUN (lecture seule, rien n'est ecrit en base).
Pour ecrire reellement : ajouter --commit

Usage (depuis le dossier backend, venv active) :
    python import_negociateurs.py Suivi_sites_OOREDOO_CENTRE.xlsx
    python import_negociateurs.py Suivi_sites_OOREDOO_CENTRE.xlsx --commit
    python import_negociateurs.py Suivi_sites_OOREDOO_CENTRE.xlsx --commit --create-missing
"""
import argparse
import asyncio
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# A REMPLIR si le script ne reconnait pas un negociateur (voir le rapport).
# Cle = nom tel qu'ecrit dans le fichier de suivi (en MAJUSCULES),
# valeur = adresse e-mail OU nom affiche du compte dans MZ Sitehub.
# Exemple :  "DJAMEL": "djamel.henni@mzbuilding.dz",
# ---------------------------------------------------------------------------
NEGOTIATOR_ALIASES = {
    "DJAMEL": "djamel.dahmane@mzbuilding.dz",
    "freelance KAMEL TAM".upper(): "Kamel FREELANCE",
    "BELKACEM": "BELKACEM",
    "FREELANCE BEJAIA": "Belkacem FREELANCE",
    "FREELANCE BELKACEM": "Belkacem FREELANCE",
}

# Valeurs de la colonne "Charge Acquisition" qui ne designent pas un negociateur
NO_NEGOTIATOR = {"", "-", "OOREDOO"}

NO_CODE_RE = re.compile(r"^PROJET\d*$")


# ----------------------------------------------------------------- utilitaires
def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")


def clean(s):
    return re.sub(r"\s+", " ", str(s if s is not None else "")).strip()


def squash(s):
    """Code compare sans accents/espaces/tirets : 'AL_Proposition1' == 'AL PROPOSITION 1'."""
    return re.sub(r"[^A-Z0-9]", "", strip_accents(s).upper())


def norm_header(s):
    return re.sub(r"[^a-z0-9]", "", strip_accents(s).lower())


def tokens(s):
    return {t for t in re.split(r"[^a-z0-9]+", strip_accents(s).lower()) if t}


def base_code(sq):
    m = re.match(r"^([A-Z]{2}\d{4})", sq)
    return m.group(1) if m else None


def parse_wilaya(text):
    m = re.search(r"\(\s*(\d+)\s*\)", str(text or ""))
    return int(m.group(1)) if m else None


def parse_delai(v):
    s = clean(v)
    if not s:
        return None
    try:
        f = float(s.replace(",", "."))
        return int(f) if f == int(f) else f
    except ValueError:
        return s


def parse_negotiator(raw):
    """Retourne (cle, est_freelance, texte_brut) ou None si pas de negociateur."""
    s = clean(raw)
    is_free = s.lower().startswith("freelance")
    name = re.sub(r"^freelance\s*", "", s, flags=re.I).strip()
    if name.upper() in NO_NEGOTIATOR or s.upper() in NO_NEGOTIATOR:
        return None
    return (name.upper(), is_free, s)


# ------------------------------------------------------------------- lecture
COLS = {
    "projet": lambda h: h == "projet",
    "code": lambda h: h == "codesite",
    "negociateur": lambda h: h.startswith("chargeacquisition") or h in ("negociateur", "chargeacq"),
    "wilaya": lambda h: h == "wilaya",
    "delai": lambda h: h.startswith("delaidocb"),
    "avancement": lambda h: h == "avancement",
    "typo": lambda h: h.startswith("typosite") or h == "typo",
    "categorie": lambda h: h == "categorie",
}


def find_header(rows):
    for i, r in enumerate(rows[:20]):
        if any(norm_header(c) == "codesite" for c in r):
            return i
    return None


def rows_from_table(table):
    hi = find_header(table)
    if hi is None:
        return None
    header = [norm_header(c) for c in table[hi]]
    idx = {}
    for key, test in COLS.items():
        for j, h in enumerate(header):
            if h and test(h):
                idx[key] = j
                break
    out = []
    for r in table[hi + 1:]:
        d = {}
        for key, j in idx.items():
            d[key] = clean(r[j]) if j < len(r) and r[j] is not None else ""
        out.append(d)
    return out, idx


def load_rows(path, sheet=None):
    p = Path(path)
    if not p.exists():
        sys.exit(f"Fichier introuvable : {p}")
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
        sheets = [wb[sheet]] if sheet else wb.worksheets
        for ws in sheets:
            table = [list(r) for r in ws.iter_rows(values_only=True)]
            res = rows_from_table(table)
            if res:
                print(f"Feuille lue : {ws.title}")
                return res
        sys.exit("Colonne 'Code Site' introuvable dans le fichier Excel.")
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    first = text.splitlines()[0] if text else ""
    delim = "\t" if "\t" in first else (";" if first.count(";") > first.count(",") else ",")
    table = list(csv.reader(text.splitlines(), delimiter=delim))
    res = rows_from_table(table)
    if not res:
        sys.exit("Colonne 'Code Site' introuvable dans le fichier.")
    return res


def dedupe(rows):
    """Une ligne par code. Si un code apparait 2 fois, les valeurs non vides les plus basses l'emportent."""
    merged, order, dups = {}, [], []
    for r in rows:
        code = clean(r.get("code"))
        if not code:
            continue
        k = squash(code)
        if k in merged:
            dups.append(code)
            for f, v in r.items():
                if clean(v):
                    merged[k][f] = v
        else:
            merged[k] = dict(r)
            order.append(k)
    return [merged[k] for k in order], dups


# ------------------------------------------------------------- rapprochements
def build_user_index(users):
    idx = []
    for u in users:
        toks = set()
        label_parts = []
        for key in ("first_name", "last_name", "full_name", "name", "prenom", "nom"):
            v = u.get(key)
            if v:
                toks |= tokens(v)
                label_parts.append(str(v))
        email = u.get("email") or ""
        if email:
            toks |= tokens(email.split("@")[0])
        idx.append({"id": str(u["id"]), "email": email.lower(),
                    "label": (" ".join(label_parts) or email), "tokens": toks})
    return idx


def match_user(neg, uidx):
    """neg = (cle, est_freelance, brut). Retourne (statut, utilisateur|liste)."""
    key, _free, raw = neg
    alias = NEGOTIATOR_ALIASES.get(raw.upper()) or NEGOTIATOR_ALIASES.get(key)
    if alias:
        a = strip_accents(alias).lower().strip()
        found = [u for u in uidx
                 if u["email"] == a or strip_accents(u["label"]).lower().strip() == a]
        if len(found) == 1:
            return "ok", found[0]
        return ("ambigu", found) if found else ("introuvable", [])
    want = tokens(key)
    if not want:
        return "introuvable", []
    cands = [u for u in uidx if want <= u["tokens"]]
    if len(cands) == 1:
        return "ok", cands[0]
    if len(cands) > 1:
        return "ambigu", cands
    return "introuvable", []


def build_plan(rows, users, sites, wilaya_ids, create_missing, keep_existing=False):
    uidx = build_user_index(users)
    by_exact, by_base = {}, {}
    for s in sites:
        sq = squash(s["code"])
        by_exact.setdefault(sq, []).append(s)
        b = base_code(sq)
        if b:
            by_base.setdefault(b, []).append(s)

    neg_cache, neg_report, plan = {}, {}, []
    for r in rows:
        code = clean(r.get("code"))
        sq = squash(code)
        entry = {"code": code, "action": "", "db_codes": "", "negociateur": clean(r.get("negociateur")),
                 "utilisateur": "", "remarque": [], "update": None, "create": None}

        if not code or NO_CODE_RE.match(sq):
            entry["action"] = "IGNORE"
            entry["remarque"].append("pas de code site officiel")
            plan.append(entry)
            continue

        # negociateur
        user = None
        neg = parse_negotiator(r.get("negociateur"))
        if neg:
            if neg[2] not in neg_cache:
                neg_cache[neg[2]] = match_user(neg, uidx)
            status, res = neg_cache[neg[2]]
            neg_report.setdefault(neg[2], [status, res, 0])[2] += 1
            if status == "ok":
                user = res
                entry["utilisateur"] = res["label"]
            elif status == "ambigu":
                entry["remarque"].append("negociateur ambigu : " + " / ".join(c["label"] for c in res))
            else:
                entry["remarque"].append("negociateur introuvable")

        cf = {}
        # La catégorie n'est volontairement PAS importée (plus à jour dans MZ Sitehub)
        for src, dst in (("projet", "projet"), ("typo", "typo_site"), ("avancement", "avancement")):
            if clean(r.get(src)):
                cf[dst] = clean(r.get(src))
        d = parse_delai(r.get("delai"))
        if d is not None:
            cf["delai_doc_b"] = d
        if neg:
            cf["negociateur_suivi"] = neg[2]
        wil = parse_wilaya(r.get("wilaya"))

        matched = by_exact.get(sq)
        how = "exact"
        if not matched:
            b = base_code(sq)
            matched = by_base.get(b) if b else None
            how = "variante A/B"
        if matched:
            entry["db_codes"] = ", ".join(s["code"] for s in matched)
            if how != "exact":
                entry["remarque"].append(f"rapproche par variante : {entry['db_codes']}")
            upd = []
            for s in matched:
                new_resp = None
                if user and s.get("responsible_user_id") and str(s["responsible_user_id"]) != user["id"]:
                    entry["remarque"].append(f"responsable change sur {s['code']}")
                if user and str(s.get("responsible_user_id") or "") != user["id"]:
                    if keep_existing and s.get("responsible_user_id"):
                        entry["remarque"].append(f"responsable conserve sur {s['code']}")
                    else:
                        new_resp = user["id"]
                new_wil = wil if (s.get("wilaya_id") is None and wil in wilaya_ids) else None
                upd.append({"site_id": str(s["id"]), "code": s["code"], "responsible": new_resp,
                            "wilaya": new_wil, "cf": cf})
            entry["action"] = "MAJ"
            entry["update"] = upd
        else:
            entry["action"] = "CREER" if create_missing else "ABSENT"
            if create_missing:
                entry["create"] = {"code": code, "wilaya": wil if wil in wilaya_ids else None,
                                   "responsible": user["id"] if user else None, "cf": cf}
        plan.append(entry)
    return plan, neg_report


# ------------------------------------------------------------------- DB / main
def read_dsn(env_path):
    p = Path(env_path)
    if not p.exists():
        sys.exit(f"Fichier .env introuvable : {p.resolve()} (lance le script depuis le dossier backend)")
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DATABASE_URL"):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            return v.replace("postgresql+asyncpg://", "postgresql://")
    sys.exit("DATABASE_URL absente du .env")


async def run(args):
    import asyncpg
    rows, idx = load_rows(args.file, args.sheet)
    missing = [k for k in ("code", "negociateur") if k not in idx]
    if missing:
        sys.exit(f"Colonnes manquantes dans le fichier : {missing}")
    rows, dups = dedupe(rows)
    print(f"{len(rows)} sites lus dans le fichier" + (f" (doublons fusionnes : {', '.join(sorted(set(dups)))})" if dups else ""))

    conn = await asyncpg.connect(read_dsn(args.env), statement_cache_size=0)
    try:
        users = [dict(r) for r in await conn.fetch("select * from users")]
        users = [u for u in users if u.get("is_active") is not False and not u.get("deleted_at")]
        sites = [dict(r) for r in await conn.fetch(
            "select id, code, wilaya_id, responsible_user_id from sites where deleted_at is null")]
        wilaya_ids = {r["id"] for r in await conn.fetch("select id from wilayas")}
        st = await conn.fetchrow("select id from site_status where code = 'NOUVEAU'")
        status_new = st["id"] if st else 1

        plan, neg_report = build_plan(rows, users, sites, wilaya_ids, args.create_missing, args.keep_existing)

        # ---------- rapport console
        print("\n=== NEGOCIATEURS ===")
        for raw, (status, res, n) in sorted(neg_report.items()):
            if status == "ok":
                print(f"  OK         {raw:<26} -> {res['label']}  ({n} sites)")
            elif status == "ambigu":
                print(f"  AMBIGU     {raw:<26} -> {' / '.join(c['label'] + ' <' + c['email'] + '>' for c in res)}  ({n} sites)")
            else:
                print(f"  INTROUVABLE {raw:<25} ({n} sites)  -> a ajouter dans Utilisateurs/Negociateurs ou dans NEGOTIATOR_ALIASES")

        counts = {}
        for e in plan:
            counts[e["action"]] = counts.get(e["action"], 0) + 1
        print("\n=== SITES ===")
        print(f"  A mettre a jour : {counts.get('MAJ', 0)}")
        print(f"  A creer         : {counts.get('CREER', 0)}")
        print(f"  Absents de la base (non crees) : {counts.get('ABSENT', 0)}")
        print(f"  Ignores         : {counts.get('IGNORE', 0)}")
        n_resp = sum(1 for e in plan if e["update"] for u in e["update"] if u["responsible"])
        print(f"  Attributions de responsable a ecrire : {n_resp}")

        report = Path("rapport_import_negociateurs.csv")
        with report.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["code_suivi", "action", "codes_en_base", "negociateur_suivi", "utilisateur", "remarques"])
            for e in plan:
                w.writerow([e["code"], e["action"], e["db_codes"], e["negociateur"], e["utilisateur"],
                            " | ".join(e["remarque"])])
        print(f"\nRapport detaille : {report.resolve()}")

        if not args.commit:
            print("\nDRY-RUN : rien n'a ete ecrit. Relance avec --commit pour appliquer.")
            return

        async with conn.transaction():
            for e in plan:
                for u in e["update"] or []:
                    await conn.execute(
                        """update sites set
                               responsible_user_id = coalesce($2::uuid, responsible_user_id),
                               wilaya_id = coalesce(wilaya_id, $3::smallint),
                               custom_fields = coalesce(custom_fields, '{}'::jsonb) || $4::jsonb,
                               updated_at = now()
                           where id = $1::uuid""",
                        u["site_id"], u["responsible"], u["wilaya"], json.dumps(u["cf"]))
                c = e["create"]
                if c:
                    await conn.execute(
                        """insert into sites (id, code, name, wilaya_id, status_id, responsible_user_id,
                                              custom_fields, created_at, updated_at)
                           values (gen_random_uuid(), $1, $1, $2::smallint, $3, $4::uuid, $5::jsonb, now(), now())""",
                        c["code"], c["wilaya"], status_new, c["responsible"], json.dumps(c["cf"]))
        print("\nECRITURE TERMINEE.")
    finally:
        await conn.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="fichier de suivi (.xlsx, .csv, .tsv, .txt)")
    ap.add_argument("--sheet", help="nom de la feuille Excel (sinon detection automatique)")
    ap.add_argument("--env", default=".env", help="chemin du .env (defaut : .env)")
    ap.add_argument("--commit", action="store_true", help="ecrire reellement en base")
    ap.add_argument("--keep-existing", action="store_true",
                    help="ne pas remplacer un responsable deja attribue (seulement remplir les sites sans responsable)")
    ap.add_argument("--create-missing", action="store_true", help="creer les sites absents de la base")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
