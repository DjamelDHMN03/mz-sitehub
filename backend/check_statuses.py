import asyncio, asyncpg

async def check():
    conn = await asyncpg.connect("postgresql://postgres.wxshokpwdpdweffjfmsv:MzBuilding2026!@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")
    rows = await conn.fetch("SELECT code, label FROM site_status ORDER BY id")
    for r in rows:
        print(dict(r))
    await conn.close()

asyncio.run(check())
