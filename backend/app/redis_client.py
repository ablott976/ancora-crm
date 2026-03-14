import redis.asyncio as redis
from app.config import settings

redis_client = None

async def init_redis():
    global redis_client
    # Assuming REDIS_URL is in your settings
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()

def get_redis():
    if not redis_client:
        raise Exception("Redis client not initialized")
    return redis_client
