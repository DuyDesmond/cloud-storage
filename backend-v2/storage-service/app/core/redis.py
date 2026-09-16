import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

redis_client: redis.Redis | None = None

def get_redis_client() -> redis.Redis | None:
    return redis_client

async def init_redis():
    global redis_client
    redis_url = settings.REDIS_URL
    redis_client = redis.from_url(redis_url, decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
