"""Integration smoke test — uses SQLite in-memory (from conftest fixtures)."""
import uuid
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import create_app
from src.db import get_session
from src.models import Tag, Source
from src.workers.pipeline import RawArticle, ingest_article
from src.workers.ranker import run_ranker


@pytest.fixture
async def seeded_session(session):
    """Add a tag and source so pipeline and ranker can work."""
    tag = Tag(id=uuid.uuid4(), name="technology", keywords=["AI", "tech"], priority=1, active=True)
    source = Source(id=uuid.uuid4(), name="TestSource", type="rss",
                    config={"feed_url": "https://example.com"}, authority_score=0.8,
                    poll_interval=60, active=True)
    session.add_all([tag, source])
    await session.commit()
    return session


async def test_pipeline_to_api(seeded_session):
    """Ingest an article through the pipeline, then read it back via the API."""
    raw = RawArticle(
        title="AI breakthrough announced",
        author="Test Author",
        source_name="TestSource",
        url=f"https://example.com/{uuid.uuid4()}",
        published_at=datetime.now(timezone.utc),
        raw_tags=["artificial-intelligence"],
    )

    with patch("src.workers.pipeline.publish_article", new_callable=AsyncMock):
        article = await ingest_article(raw, seeded_session)

    assert article is not None
    assert "technology" in article.matched_tags

    # Now query via API
    app = create_app()

    async def override():
        yield seeded_session

    app.dependency_overrides[get_session] = override

    with patch("src.api.websocket.redis_listener", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/articles")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) >= 1
            assert any(a["title"] == "AI breakthrough announced" for a in data)

            # Run ranker
            await run_ranker(seeded_session)

            # Check top articles
            resp = await client.get("/articles/top")
            assert resp.status_code == 200
            top = resp.json()
            assert len(top) >= 1
            assert top[0]["relevance_score"] > 0
