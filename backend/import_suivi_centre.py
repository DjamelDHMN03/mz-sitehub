"""Import du suivi Ooredoo Centre dans sites. SIMULATION par defaut ; --apply pour enregistrer."""
import asyncio, csv, json, re, sys, uuid
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from openpyxl import load_workbook

SHEET = "Sites"
LON_RANGE = (-9.0, 12.5)
LAT_RANGE = (18.5, 38.0)
REPORT = "rapport_import_centre.csv"

def clean(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = re.sub(r"\s+", " ", v.replace("\u00a0", " ")).strip()
        return v or None
    return v

def norm_key(v):
    v = clean(v)
    return "(VIDE)" if v is None else str(v).upper()

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
    v = clean(v)
    if isinstance(v, str):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                pass
    return None

def clean_phone(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) == 9 and digits[0] in "567":
        return "0" + digits
    return clean(s)

def clean_rent(v):
    v = clean(v)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.,]", "", str(v))
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def pick_coords(r, warns):
    for lon_k, lat_k in (("GPS LONG", "GPS LAT"), ("GPS LONG POINT NOMINAL", "GPS LAT POINT NOMINAL")):
        lon, lat = to_float(r.get(lon_k)), to_float(r.get(lat_k))
        if lon is None or lat is None:
            if clean(r.get(lon_k)) is not None or clean(r.get(lat_k)) is not None:
                warns.append(f"GPS illisible ({lon_k}/{lat_k})")
            continue
        if LON_RANGE[0] <= lon <= LON_RANGE[1] and LAT_RANGE[0] <= lat <= LAT_RANGE[1]:
            return lon, lat
        if LON_RANGE[0] <= lat <= LON_RANGE[1] and LAT_RANGE[0] <= lon <= LAT_RANGE[1]:
            warns.append("GPS lon/lat inverses, corriges")
            return lat, lon
        warns.append(f"GPS hors Algerie ({lon}, {lat})")
    return None, None

def negotiator_kind(name):
    if name.lower().startswith("freelance"):
        return "FREELANCE"
    if name.upper() == "OOREDOO":
        return "OPERATEUR"
    return "INTERNE"

def parse_suivi(path, rules, wilaya_ids):
    wb = load_workbook(path, data_only=True, read_only=True)
    ws = wb[SHEET]
    rows = ws.iter_rows(values_only=True)
    header = [clean(h) for h in next(rows)]
    by_code, dups, n_lines = {}, [], 0
    for line, raw in enumerate(rows, start=2):
        r = {h: v for h, v in zip(header, raw) if h}
        code = clean(r.get("Code Site"))
        if not code:
            continue
        n_lines += 1
        code = str(code).upper()
        score = sum(1 for v in r.values() if clean(v) is not None)
        if code in by_code:
            dups.append(code)
            if score >= by_code[code][0]:
                by_code[code] = (score, line, r)
        else:
            by_code[code] = (score, line, r)
    out = []
    for code, (_score, line, r) in sorted(by_code.items()):
        warns = []
        key = norm_key(r.get("AVANCEMENT"))
        rule = rules.get(key)
        if rule is None:
            warns.append(f"avancement inconnu: {key}")
            rule = ("EN_COURS", None, None, None)
        category, stage, waiting, rule_status = rule
        wil = None
        m = re.search(r"\((\d+)\)", str(r.get("WILAYA") or ""))
        if m:
            wid = int(m.group(1))
            if wid in wilaya_ids:
                wil = wid
            else:
                warns.append(f"wilaya inconnue: {r.get('WILAYA')}")
        lon, lat = pick_coords(r, warns)
        nom = clean(r.get("Charg\u00e9 Acquisition"))
        delay = to_float(r.get("D\u00e9lai DOC B"))
        delay = int(delay) if delay is not None else None
        d_a, d_b = to_date(r.get("DOC A Date")), to_date(r.get("DOC B Date"))
        type_prop = clean(r.get("Type Propri\u00e9t\u00e9"))
        type_prop = type_prop.upper() if type_prop else None
        if type_prop == "LES DOMAINES":
            type_prop = "DOMAINES"
        custom = {}
        if clean(r.get("Rapport Zone")) is not None:
            custom["rapport_zone"] = str(clean(r.get("Rapport Zone")))
        project = clean(r.get("PROJET"))
        entity = clean(r.get("ACQUISITION"))
        out.append({
            "code": code, "line": line,
            "project": project.upper() if project else None,
            "entity": entity.upper() if entity else None,
            "negotiator": nom, "kind": negotiator_kind(nom) if nom else None,
            "wilaya_id": wil, "commune_name": clean(r.get("COMMUNE")),
            "owner_type": type_prop, "owner_name": clean(r.get("Nom Candidat")),
            "address": clean(r.get("Adresse")), "phone": clean_phone(r.get("Telephone")),
            "rent": clean_rent(r.get("Loyer N\u00e9goci\u00e9")),
            "lon": lon, "lat": lat, "doc_a": d_a, "doc_b": d_b, "delay": delay,
            "tss": to_date(r.get("TSS Date")), "contract": to_date(r.get("Contrat Date")),
            "typology": clean(r.get("Typo Site")), "model": clean(r.get("Type Site")),
            "observation": clean(r.get("REMARQUES")),
            "progress_raw": clean(r.get("AVANCEMENT")),
            "category": category, "stage": stage, "waiting": waiting,
            "rule_status": rule_status, "custom": custom, "warns": warns,
        })
    return out, dups, n_lines

def build_insert(table, fields, constants):
    cols, ph, args = [], [], []
    for col, tpl, val in fields:
        args.append(val)
        cols.append(col)
        ph.append(tpl.format(f"${len(args)}"))
    for col, expr in constants:
        cols.append(col)
        ph.append(expr)
    return f"insert into {table} ({', '.join(cols)}) values ({', '.join(ph)})", args

def build_update(table, fields, constants, where_id):
    sets, args = [], [where_id]
    for col, tpl, val in fields:
        args.append(val)
        sets.append(f"{col} = {tpl.format('$' + str(len(args)))}")
    for col, expr in constants:
        sets.append(f"{col} = {expr}")
    return f"update {table} set {', '.join(sets)} where id = $1", args

def db_url():
    for line in open(".env", encoding="utf-8"):
        if line.startswith("DATABASE_URL"):
            return line.split("=", 1)[1].strip().replace("+asyncpg", "")
    raise SystemExit("DATABASE_URL introuvable dans .env")

async def main():
    import asyncpg
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if not args:
        raise SystemExit('Usage : python import_suivi_centre.py "fichier.xlsx" [--apply]')
    path = args[0]
    conn = await asyncpg.connect(db_url())
    ok = await conn.fetchval("select 1 from information_schema.columns where table_schema='public' and table_name='sites' and column_name='progress_raw'")
    if not ok:
        raise SystemExit("Migration 002 non appliquee : lancez d'abord apply_migration.py ... --apply")
    rules = {r["progress_key"]: (r["category"], r["stage"], r["waiting_for"], r["status_id"]) for r in await conn.fetch("select * from progress_rules")}
    wilaya_ids = {r["id"] for r in await conn.fetch("select id from wilayas")}
    records, dups, n_lines = parse_suivi(path, rules, wilaya_ids)
    existing = {r["code"].upper(): r for r in await conn.fetch("select id, code, status_id from sites where deleted_at is null")}
    tr = conn.transaction()
    await tr.start()
    report, n_create, n_update, n_status = [], 0, 0, 0
    try:
        neg_ids = {}
        for nm, kind in sorted({(x["negotiator"], x["kind"]) for x in records if x["negotiator"]}):
            neg_ids[nm] = await conn.fetchval("insert into negotiators (name, kind) values ($1, $2) on conflict (name) do update set kind = excluded.kind returning id", nm, kind)
        for x in records:
            nid = neg_ids.get(x["negotiator"])
            wkt = f"SRID=4326;POINT({x['lon']} {x['lat']})" if x["lon"] is not None else None
            rent = Decimal(str(x["rent"])) if x["rent"] is not None else None
            common = [
                ("project", "{}", x["project"]), ("acquisition_entity", "{}", x["entity"]),
                ("negotiator_id", "{}", nid), ("owner_type", "{}", x["owner_type"]),
                ("commune_name", "{}", x["commune_name"]), ("rent_negotiated", "{}", rent),
                ("doc_a_date", "{}", x["doc_a"]), ("doc_b_date", "{}", x["doc_b"]),
                ("doc_b_delay_days", "{}", x["delay"]), ("tss_date", "{}", x["tss"]),
                ("contract_date", "{}", x["contract"]), ("site_typology", "{}", x["typology"]),
                ("site_model", "{}", x["model"]), ("progress_raw", "{}", x["progress_raw"]),
                ("progress_category", "{}", x["category"]), ("progress_stage", "{}", x["stage"]),
                ("waiting_for", "{}", x["waiting"]),
            ]
            ex = existing.get(x["code"])
            status_note = ""
            if ex:
                fields = common + [
                    ("owner_phone", "coalesce(owner_phone, {})", x["phone"]),
                    ("owner_name", "coalesce(owner_name, {})", x["owner_name"]),
                    ("address", "coalesce(address, {})", x["address"]),
                    ("observation", "coalesce(observation, {})", x["observation"]),
                    ("wilaya_id", "coalesce(wilaya_id, {})", x["wilaya_id"]),
                    ("geom", "coalesce(geom, ({}::text)::geometry)", wkt),
                    ("custom_fields", "coalesce(custom_fields, '{{}}'::jsonb) || {}::jsonb", json.dumps(x["custom"])),
                    ("status_id", "coalesce({}::int, status_id)", x["rule_status"]),
                ]
                sql, a = build_update("sites", fields, [("updated_at", "now()")], ex["id"])
                await conn.execute(sql, *a)
                n_update += 1
                action = "MISE A JOUR"
                if x["rule_status"] and x["rule_status"] != ex["status_id"]:
                    n_status += 1
                    status_note = f"statut {ex['status_id']} -> {x['rule_status']}"
                    try:
                        async with conn.transaction():
                            await conn.execute("insert into site_history (id, site_id, field, old_value, new_value, changed_at) values ($1, $2, 'status_id', $3, $4, now())", uuid.uuid4(), ex["id"], str(ex["status_id"]), str(x["rule_status"]))
                    except Exception as exc:
                        x["warns"].append(f"historique non ecrit: {type(exc).__name__}")
            else:
                fields = [
                    ("id", "{}", uuid.uuid4()), ("code", "{}", x["code"]),
                    ("wilaya_id", "{}", x["wilaya_id"]), ("address", "{}", x["address"]),
                    ("geom", "({}::text)::geometry", wkt), ("owner_name", "{}", x["owner_name"]),
                    ("status_id", "{}", x["rule_status"] or 1), ("observation", "{}", x["observation"]),
                    ("custom_fields", "{}::jsonb", json.dumps(x["custom"])), ("owner_phone", "{}", x["phone"]),
                ] + common
                consts = [("previous_codes", "'{}'::text[]"), ("priority", "2"), ("is_favorite", "false"), ("created_at", "now()"), ("updated_at", "now()")]
                sql, a = build_insert("sites", fields, consts)
                await conn.execute(sql, *a)
                n_create += 1
                action = "CREATION"
            report.append([x["code"], action, x["category"], x["stage"] or "", x["waiting"] or "", x["negotiator"] or "", x["wilaya_id"] or "", "oui" if x["lon"] is not None else "non", status_note, " | ".join(x["warns"])])
        by_cat = await conn.fetch("select coalesce(progress_category,'(non renseigne)') as c, count(*) as n from sites where deleted_at is null group by 1 order by 1")
        if apply:
            await tr.commit()
        else:
            await tr.rollback()
    except Exception as exc:
        await tr.rollback()
        print("ERREUR, tout a ete annule :", type(exc).__name__, exc)
        await conn.close()
        raise SystemExit(1)
    with open(REPORT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["code", "action", "categorie", "etape", "attend", "negociateur", "wilaya_id", "gps", "changement_statut", "avertissements"])
        w.writerows(report)
    suivi_codes = {x["code"] for x in records}
    absent = sorted(set(existing) - suivi_codes)
    tests = [c for c in absent if re.search(r"XXX|PROPOSITION", c)]
    variantes = sorted((c, s) for c in absent for s in suivi_codes if s != c and (re.fullmatch(re.escape(c) + r"[A-Z]", s) or re.fullmatch(re.escape(s) + r"[A-Z]", c)))
    cats = Counter(x["category"] for x in records)
    warn_kinds = Counter(w.split(":")[0].split("(")[0].strip() for x in records for w in x["warns"])
    print(("ENREGISTRE" if apply else "SIMULATION (rien n'est enregistre)"), "- fichier :", path)
    print(f"Lignes avec code : {n_lines} | sites uniques : {len(records)} | doublons resolus : {sorted(set(dups))}")
    print(f"A creer : {n_create} | a mettre a jour : {n_update} | changements de statut : {n_status}")
    print("Categories (sites du suivi) :", dict(cats))
    print("Avertissements :", dict(warn_kinds) if warn_kinds else "aucun")
    print("Sites en base absents du suivi :", len(absent))
    print("   fiches de test probables :", tests)
    print("   variantes avec lettre :", variantes)
    print("Etat de la table sites apres import :", {r["c"]: r["n"] for r in by_cat})
    print(f"Rapport detaille : {REPORT}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
