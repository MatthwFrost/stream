# backend/src/services/redis_pubsub.py
import json
import redis.asyncio as aioredis
from src.config import settings

CHANNEL = "new_article"


async def get_redis(redis_url: str | None = None) -> aioredis.Redis:
    return aioredis.from_url(redis_url or settings.redis_url)


async def publish_article(article_data: dict, redis_url: str | None = None) -> None:
    """Publish a new article event to the Redis channel."""
    r = await get_redis(redis_url)
    await r.publish(CHANNEL, json.dumps(article_data, default=str))
    await r.aclose()


async def subscribe_articles(redis_url: str | None = None):
    """Yield article dicts as they arrive on the Redis channel."""
    r = await get_redis(redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()
        await r.aclose()
