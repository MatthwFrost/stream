import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import create_app
from src.db import get_session
from src.models import Article


@pytest.fixture
def app(session):
    application = create_app()

    async def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    return application


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
async def seed_articles(session: AsyncSession):
    articles = []
    for i in range(5):
        a = Article(
            id=uuid.uuid4(),
            title=f"Article {i}",
            author=f"Author {i}",
            source_name="Reuters" if i % 2 == 0 else "BBC",
            url=f"https://example.com/article-{i}",
            is_paywalled=i == 0,
            published_at=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            relevance_score=float(i) / 5,
            raw_tags=[],
            matched_tags=["technology"] if i % 2 == 0 else [],
        )
        articles.append(a)
    session.add_all(articles)
    await session.commit()
    return articles


async def test_get_articles(client, seed_articles):
    resp = await client.get("/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5


async def test_get_articles_with_tag_filter(client, seed_articles):
    resp = await client.get("/articles", params={"tag": "technology"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3  # Articles 0, 2, 4


async def test_get_top_articles(client, seed_articles):
    resp = await client.get("/articles/top")
    assert resp.status_code == 200
    data = resp.json()
    scores = [a["relevance_score"] for a in data]
    assert scores == sorted(scores, reverse=True)
