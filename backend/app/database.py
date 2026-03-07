import asyncpg
from app.config import settings

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(dsn=settings.database_url)

async def close_db():
    global pool
    if pool:
        await pool.close()

async def get_db():
    if not pool:
        raise Exception("Database pool not initialized")
    async with pool.acquire() as conn:
        yield conn
