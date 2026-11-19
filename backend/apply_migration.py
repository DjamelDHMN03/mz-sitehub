import asyncio, pathlib, re, sys
import asyncpg

def db_url():
    for line in open(".env", encoding="utf-8"):
        if line.startswith("DATABASE_URL"):
            return line.split("=", 1)[1].strip().replace("+asyncpg", "")
    raise SystemExit("DATABASE_URL introuvable dans .env")

async def main():
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if not files:
        raise SystemExit("Usage : python apply_migration.py fichier.sql [--apply]")
    sql = pathlib.Path(files[0]).read_text(encoding="utf-8-sig")
    sql = re.sub(r"^\s*(BEGIN|COMMIT)\s*;\s*$", "", sql, flags=re.M | re.I)
    conn = await asyncpg.connect(db_url())
    tr = conn.transaction()
    await tr.start()
    try:
        await conn.execute(sql)
        n_rules = await conn.fetchval("select count(*) from progress_rules")
        n_neg = await conn.fetchval("select count(*) from negotiators")
        n_cols = await conn.fetchval("select count(*) from information_schema.columns where table_schema='public' and table_name='sites'")
        n_sites = await conn.fetchval("select count(*) from sites")
        print(f"Etat dans la transaction : progress_rules={n_rules} | negotiators={n_neg} | colonnes de sites={n_cols} | lignes de sites={n_sites}")
        if apply:
            await tr.commit()
            print("MIGRATION APPLIQUEE.")
        else:
            await tr.rollback()
            print("SIMULATION terminee : rien n'a ete enregistre.")
            print("Relancez avec --apply pour appliquer.")
    except Exception as exc:
        await tr.rollback()
        print("ERREUR, tout a ete annule :", type(exc).__name__, exc)
        await conn.close()
        raise SystemExit(1)
    rows = await conn.fetch("select tablename from pg_tables where schemaname='public' and not rowsecurity order by 1")
    names = [r["tablename"] for r in rows]
    print(f"\nTables du schema public SANS securite par ligne ({len(names)}) :")
    print(", ".join(names) if names else "(aucune)")
    await conn.close()

asyncio.run(main())
