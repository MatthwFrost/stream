import uuid
from datetime import datetime, timezone

import pytest
from src.models import Article, Tag, Source


async def test_create_article(session):
    article = Article(
        id=uuid.uuid4(),
        title="Test Article",
        author="Test Author",
        source_name="Reuters",
        url="https://example.com/article-1",
        is_paywalled=False,
        published_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        relevance_score=0.0,
        raw_tags=["tech"],
        matched_tags=["technology"],
    )
    session.add(article)
    await session.commit()

    result = await session.get(Article, article.id)
    assert result is not None
    assert result.title == "Test Article"
    assert result.source_name == "Reuters"
    assert result.matched_tags == ["technology"]


async def test_create_tag(session):
    tag = Tag(
        id=uuid.uuid4(),
        name="technology",
        keywords=["tech", "AI", "software"],
        priority=1,
        active=True,
    )
    session.add(tag)
    await session.commit()

    result = await session.get(Tag, tag.id)
    assert result is not None
    assert result.name == "technology"
    assert "AI" in result.keywords


async def test_create_source(session):
    source = Source(
        id=uuid.uuid4(),
        name="Reuters",
        type="rss",
        config={"feed_url": "https://feeds.reuters.com/reuters/topNews"},
        authority_score=1.0,
        poll_interval=60,
        active=True,
    )
    session.add(source)
    await session.commit()

    result = await session.get(Source, source.id)
    assert result is not None
    assert result.name == "Reuters"
    assert result.config["feed_url"] == "https://feeds.reuters.com/reuters/topNews"


async def test_article_url_unique(session):
    import sqlalchemy

    a1 = Article(
        id=uuid.uuid4(),
        title="First",
        source_name="Reuters",
        url="https://example.com/dupe",
        is_paywalled=False,
        published_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        relevance_score=0.0,
        raw_tags=[],
        matched_tags=[],
    )
    a2 = Article(
        id=uuid.uuid4(),
        title="Second",
        source_name="BBC",
        url="https://example.com/dupe",
        is_paywalled=False,
        published_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        relevance_score=0.0,
        raw_tags=[],
        matched_tags=[],
    )
    session.add(a1)
    await session.commit()
    session.add(a2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        await session.commit()
