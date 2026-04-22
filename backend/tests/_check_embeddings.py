import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import create_pool, close_pool, get_pool

async def check():
    await create_pool()
    pool = await get_pool()
    row = await pool.fetchval("SELECT COUNT(*) FROM schema_embeddings")
    print(f"schema_embeddings rows: {row}")
    if row > 0:
        sample = await pool.fetch("SELECT table_name, column_name, description FROM schema_embeddings LIMIT 3")
        for r in sample:
            print(f"  {r['table_name']}.{r['column_name']}: {r['description'][:60]}")
    else:
        print("TABLE IS EMPTY! Embeddings need to be re-seeded.")
    await close_pool()

asyncio.run(check())
