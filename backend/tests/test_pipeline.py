import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Article, Tag
from src.workers.pipeline import ingest_article, RawArticle


@pytest.fixture
async def seed_tags(session):
    tags = [
        Tag(id=uuid.uuid4(), name="technology", keywords=["tech", "AI", "software"], priority=1, active=True),
        Tag(id=uuid.uuid4(), name="oil", keywords=["oil", "petroleum", "OPEC"], priority=1, active=True),
    ]
    session.add_all(tags)
    await session.commit()
    return tags


async def test_ingest_new_article(session, seed_tags):
    raw = RawArticle(
        title="New AI Breakthrough",
        author="Jane Doe",
        source_name="TechCrunch",
        url="https://techcrunch.com/ai-breakthrough",
        published_at=datetime.now(timezone.utc),
        raw_tags=["artificial intelligence"],
    )

    with patch("src.workers.pipeline.publish_article", new_callable=AsyncMock) as mock_pub:
        result = await ingest_article(raw, session)

    assert result is not None
    assert result.title == "New AI Breakthrough"
    assert "technology" in result.matched_tags
    assert result.is_paywalled is False
    mock_pub.assert_called_once()


async def test_ingest_duplicate_skipped(session, seed_tags):
    raw = RawArticle(
        title="Duplicate Article",
        author=None,
        source_name="Reuters",
        url="https://example.com/dupe",
        published_at=datetime.now(timezone.utc),
        raw_tags=[],
    )

    with patch("src.workers.pipeline.publish_article", new_callable=AsyncMock):
        first = await ingest_article(raw, session)
        second = await ingest_article(raw, session)

    assert first is not None
    assert second is None


async def test_ingest_detects_paywall(session, seed_tags):
    raw = RawArticle(
        title="Market Analysis",
        author="John Smith",
        source_name="WSJ",
        url="https://www.wsj.com/articles/market-analysis",
        published_at=datetime.now(timezone.utc),
        raw_tags=[],
    )

    with patch("src.workers.pipeline.publish_article", new_callable=AsyncMock):
        result = await ingest_article(raw, session)

    assert result is not None
    assert result.is_paywalled is True
