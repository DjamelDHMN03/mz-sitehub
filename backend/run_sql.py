import asyncio
import sys
from pathlib import Path

import asyncpg


def get_dsn():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DATABASE_URL"):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            return v.replace("postgresql+asyncpg://", "postgresql://")
    sys.exit("DATABASE_URL absente du .env")


async def main(path):
    sql = Path(path).read_text(encoding="utf-8")
    conn = await asyncpg.connect(get_dsn(), statement_cache_size=0)
    try:
        await conn.execute(sql)
        n = await conn.fetchval("select count(*) from site_visits")
        print(f"OK : table site_visits prete ({n} ligne(s))")
    finally:
        await conn.close()


asyncio.run(main(sys.argv[1]))
