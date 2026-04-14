import json
import pytest
import redis.asyncio as aioredis
from src.services.redis_pubsub import publish_article, subscribe_articles

REDIS_URL = "redis://localhost:6379/1"  # Use DB 1 for tests


@pytest.fixture
async def redis_client():
    client = aioredis.from_url(REDIS_URL)
    yield client
    await client.flushdb()
    await client.aclose()


async def test_publish_and_receive(redis_client):
    article_data = {
        "id": "test-uuid",
        "title": "Test Article",
        "source_name": "Reuters",
        "url": "https://example.com/test",
    }

    # Subscribe first
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("new_article")

    # Consume the subscription confirmation message
    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

    # Publish
    await publish_article(article_data, redis_url=REDIS_URL)

    # Receive
    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=2.0)
    assert msg is not None
    assert msg["type"] == "message"
    payload = json.loads(msg["data"])
    assert payload["title"] == "Test Article"

    await pubsub.unsubscribe("new_article")
    await pubsub.aclose()
