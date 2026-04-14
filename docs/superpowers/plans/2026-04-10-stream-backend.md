# Stream Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a VPS-hosted backend that continuously ingests news articles from RSS feeds, news APIs, and scrapers, ranks them, and pushes them to connected clients over WebSocket.

**Architecture:** Two-process Python backend — a FastAPI API server (WebSocket + REST) and a separate worker process running ingestion agents and a ranker. PostgreSQL stores articles/tags/sources. Redis pub/sub bridges worker→API for real-time push.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, Redis (pub/sub), feedparser, httpx, BeautifulSoup4, Docker Compose

---

## File Structure

```
backend/
├── pyproject.toml                      # Dependencies + project config
├── .env.example                        # Env var template
├── Dockerfile                          # Multi-stage Python image
├── docker-compose.yml                  # api + worker + postgres + redis + nginx
├── nginx.conf                          # Reverse proxy config
├── alembic.ini                         # Alembic config
├── alembic/
│   ├── env.py                          # Async Alembic env
│   └── versions/                       # Migration files
├── src/
│   ├── __init__.py
│   ├── config.py                       # Pydantic settings from env vars
│   ├── db.py                           # Async SQLAlchemy engine + session factory
│   ├── models.py                       # SQLAlchemy ORM models (articles, tags, sources)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tag_matcher.py              # Match article text against user tags
│   │   ├── paywall.py                  # Detect paywalled articles
│   │   └── redis_pubsub.py            # Publish + subscribe helpers
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── main.py                     # Worker entry point — schedules all agents + ranker
│   │   ├── pipeline.py                 # Shared ingest pipeline (normalize → dedupe → tag → paywall → store → publish)
│   │   ├── ranker.py                   # Compute relevance_score for articles
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── rss.py                  # RSS/Atom feed agent
│   │       ├── newsapi.py              # NewsAPI/GNews agent
│   │       └── scraper.py              # Web scraper agent
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app, lifespan, CORS
│   │   ├── websocket.py               # WebSocket endpoint + Redis subscriber
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── articles.py             # GET /articles, GET /articles/top
│   │       ├── tags.py                 # CRUD /tags
│   │       └── sources.py              # GET/POST /sources
│   └── seed.py                         # Seed initial sources + tags
└── tests/
    ├── conftest.py                     # Fixtures: async engine, session, test client
    ├── test_models.py
    ├── test_tag_matcher.py
    ├── test_paywall.py
    ├── test_pipeline.py
    ├── test_ranker.py
    ├── test_rss_agent.py
    ├── test_newsapi_agent.py
    ├── test_api_articles.py
    ├── test_api_tags.py
    ├── test_api_sources.py
    └── test_websocket.py
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/src/__init__.py`
- Create: `backend/src/config.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "stream-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.30.0",
    "alembic>=1.13.0",
    "redis[hiredis]>=5.0.0",
    "pydantic-settings>=2.3.0",
    "feedparser>=6.0.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create .env.example**

```env
DATABASE_URL=postgresql+asyncpg://stream:stream@localhost:5432/stream
REDIS_URL=redis://localhost:6379/0
NEWSAPI_KEY=
GNEWS_API_KEY=
```

- [ ] **Step 3: Create config.py**

```python
# backend/src/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://stream:stream@localhost:5432/stream"
    redis_url: str = "redis://localhost:6379/0"
    newsapi_key: str = ""
    gnews_api_key: str = ""

    # For tests — override with sqlite+aiosqlite
    test_mode: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: Create empty __init__.py files**

```bash
mkdir -p backend/src/services backend/src/workers/agents backend/src/api/routes backend/tests
touch backend/src/__init__.py backend/src/services/__init__.py backend/src/workers/__init__.py
touch backend/src/workers/agents/__init__.py backend/src/api/__init__.py backend/src/api/routes/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
cd backend && pip install -e ".[dev]"
```

- [ ] **Step 6: Verify imports work**

```bash
cd backend && python -c "from src.config import settings; print(settings.database_url)"
```

Expected: prints the default database URL

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project with dependencies and config"
```

---

### Task 2: Database Models

**Files:**
- Create: `backend/src/db.py`
- Create: `backend/src/models.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.models import Base


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as sess:
        yield sess
```

```python
# backend/tests/test_models.py
import uuid
from datetime import datetime, timezone
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
    """Two articles with the same URL should violate unique constraint."""
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_models.py -v
```

Expected: FAIL — `models` module doesn't exist yet

- [ ] **Step 3: Implement db.py**

```python
# backend/src/db.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
```

- [ ] **Step 4: Implement models.py**

```python
# backend/src/models.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    is_paywalled: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    raw_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    matched_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # rss, api, scraper
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    authority_score: Mapped[float] = mapped_column(Float, default=0.5)
    poll_interval: Mapped[int] = mapped_column(Integer, default=60)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_models.py -v
```

Note: Tests use SQLite in-memory which doesn't support ARRAY/JSONB natively. The conftest uses `create_all` which will create simplified columns. If tests fail on ARRAY, we'll add a `conftest.py` type adaptation. If they do fail, update the models to use JSON type with a `TypeDecorator` that serializes lists, or adjust the test to use postgres via docker. For simplicity in tests, we may need to conditionally use JSON instead of ARRAY — see step 5a.

- [ ] **Step 5a: If ARRAY fails with SQLite, add type adaptation**

If tests fail because SQLite doesn't support ARRAY, update conftest.py to use a real Postgres test database via Docker, or switch test models to use JSON columns. The simplest fix: use a Postgres container for tests.

Update `conftest.py`:

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.models import Base

TEST_DB_URL = "postgresql+asyncpg://stream:stream@localhost:5432/stream_test"


@pytest.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
```

Add a `docker-compose.test.yml` or just ensure `docker-compose.yml` includes a test database. For now, tests require a running Postgres — the docker-compose in Task 18 provides this.

- [ ] **Step 6: Commit**

```bash
git add backend/src/db.py backend/src/models.py backend/tests/conftest.py backend/tests/test_models.py
git commit -m "feat: add SQLAlchemy models for articles, tags, and sources"
```

---

### Task 3: Alembic Migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: Initialize Alembic**

```bash
cd backend && alembic init alembic
```

- [ ] **Step 2: Update alembic.ini**

Replace the `sqlalchemy.url` line:

```ini
# leave empty — set from env.py
sqlalchemy.url =
```

- [ ] **Step 3: Update alembic/env.py for async**

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings
from src.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

```bash
cd backend && alembic revision --autogenerate -m "initial tables"
```

- [ ] **Step 5: Apply migration (requires running Postgres)**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic async migrations with initial schema"
```

---

### Task 4: Tag Matcher Service

**Files:**
- Create: `backend/src/services/tag_matcher.py`
- Create: `backend/tests/test_tag_matcher.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_tag_matcher.py
from src.services.tag_matcher import match_tags


def test_matches_single_tag():
    tags = [
        {"name": "technology", "keywords": ["tech", "AI", "software"], "priority": 1},
    ]
    result = match_tags("New AI software released today", tags)
    assert result == ["technology"]


def test_matches_multiple_tags():
    tags = [
        {"name": "technology", "keywords": ["tech", "AI", "software"], "priority": 1},
        {"name": "politics", "keywords": ["election", "congress", "senate"], "priority": 1},
    ]
    result = match_tags("AI policy debated in congress", tags)
    assert "technology" in result
    assert "politics" in result


def test_no_match_returns_empty():
    tags = [
        {"name": "oil", "keywords": ["oil", "petroleum", "OPEC"], "priority": 1},
    ]
    result = match_tags("New smartphone announced", tags)
    assert result == []


def test_case_insensitive_matching():
    tags = [
        {"name": "technology", "keywords": ["AI"], "priority": 1},
    ]
    result = match_tags("ai is changing the world", tags)
    assert result == ["technology"]


def test_word_boundary_matching():
    """'oil' should not match 'soiled' or 'foil'."""
    tags = [
        {"name": "oil", "keywords": ["oil"], "priority": 1},
    ]
    assert match_tags("oil prices rise", tags) == ["oil"]
    assert match_tags("the soiled ground", tags) == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_tag_matcher.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement tag_matcher.py**

```python
# backend/src/services/tag_matcher.py
import re


def match_tags(text: str, tags: list[dict]) -> list[str]:
    """Match text against tag keyword lists. Returns list of matched tag names.

    Args:
        text: Article title or text to match against.
        tags: List of dicts with 'name' and 'keywords' keys.
    """
    matched = []
    text_lower = text.lower()
    for tag in tags:
        for keyword in tag["keywords"]:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched.append(tag["name"])
                break  # One keyword match is enough for this tag
    return matched
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_tag_matcher.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/tag_matcher.py backend/tests/test_tag_matcher.py
git commit -m "feat: add tag matcher service with word-boundary matching"
```

---

### Task 5: Paywall Detection Service

**Files:**
- Create: `backend/src/services/paywall.py`
- Create: `backend/tests/test_paywall.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_paywall.py
from src.services.paywall import is_paywalled


def test_known_paywall_domain():
    assert is_paywalled("https://www.wsj.com/articles/some-article") is True
    assert is_paywalled("https://www.ft.com/content/some-article") is True
    assert is_paywalled("https://www.bloomberg.com/news/some-article") is True


def test_known_free_domain():
    assert is_paywalled("https://www.reuters.com/article/some-article") is False
    assert is_paywalled("https://www.bbc.com/news/some-article") is False


def test_unknown_domain_defaults_free():
    assert is_paywalled("https://randomnews.example.com/article") is False


def test_respects_header_override():
    """If headers indicate paywall, override domain check."""
    assert is_paywalled(
        "https://free-site.com/article",
        headers={"X-Paywall": "true"},
    ) is True


def test_header_override_free():
    assert is_paywalled(
        "https://free-site.com/article",
        headers={"X-Paywall": "false"},
    ) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_paywall.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement paywall.py**

```python
# backend/src/services/paywall.py
from urllib.parse import urlparse

PAYWALL_DOMAINS = {
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "nytimes.com",
    "washingtonpost.com",
    "economist.com",
    "barrons.com",
    "hbr.org",
    "thetimes.co.uk",
    "telegraph.co.uk",
    "theathletic.com",
    "businessinsider.com",
    "seekingalpha.com",
    "foreignaffairs.com",
    "wired.com",
    "theatlantic.com",
}


def is_paywalled(url: str, headers: dict | None = None) -> bool:
    """Detect whether an article is behind a paywall.

    Checks:
    1. HTTP response headers (X-Paywall) if provided — takes priority.
    2. Known paywall domain list.
    """
    if headers:
        paywall_header = headers.get("X-Paywall", "").lower()
        if paywall_header == "true":
            return True
        if paywall_header == "false":
            return False

    hostname = urlparse(url).hostname or ""
    # Strip www. prefix for matching
    hostname = hostname.removeprefix("www.")

    return hostname in PAYWALL_DOMAINS
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_paywall.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/paywall.py backend/tests/test_paywall.py
git commit -m "feat: add paywall detection service with domain list and header check"
```

---

### Task 6: Redis Pub/Sub Service

**Files:**
- Create: `backend/src/services/redis_pubsub.py`
- Create: `backend/tests/test_redis_pubsub.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_redis_pubsub.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_redis_pubsub.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement redis_pubsub.py**

```python
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
    """Yield article dicts as they arrive on the Redis channel.

    This is an async generator — use `async for article in subscribe_articles():`.
    """
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
```

- [ ] **Step 4: Run tests to verify they pass (requires running Redis)**

```bash
cd backend && python -m pytest tests/test_redis_pubsub.py -v
```

Expected: PASS (requires Redis on localhost:6379)

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/redis_pubsub.py backend/tests/test_redis_pubsub.py
git commit -m "feat: add Redis pub/sub service for real-time article push"
```

---

### Task 7: Ingestion Pipeline

**Files:**
- Create: `backend/src/workers/pipeline.py`
- Create: `backend/tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_pipeline.py
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Article, Tag
from src.workers.pipeline import ingest_article, RawArticle


@pytest.fixture
async def seed_tags(session: AsyncSession):
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
    assert second is None  # Duplicate — skipped


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_pipeline.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement pipeline.py**

```python
# backend/src/workers/pipeline.py
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Article, Tag
from src.services.paywall import is_paywalled
from src.services.tag_matcher import match_tags
from src.services.redis_pubsub import publish_article


@dataclass
class RawArticle:
    title: str
    source_name: str
    url: str
    published_at: datetime
    author: str | None = None
    raw_tags: list[str] | None = None


async def ingest_article(raw: RawArticle, session: AsyncSession) -> Article | None:
    """Process a raw article through the shared pipeline.

    Returns the Article if inserted, None if duplicate.
    Pipeline: dedupe → tag match → paywall detect → store → publish.
    """
    # 1. Deduplicate by URL
    existing = await session.execute(select(Article).where(Article.url == raw.url))
    if existing.scalar_one_or_none() is not None:
        return None

    # 2. Load active tags and match
    tag_rows = await session.execute(select(Tag).where(Tag.active.is_(True)))
    tags = [{"name": t.name, "keywords": t.keywords, "priority": t.priority} for t in tag_rows.scalars()]
    matched = match_tags(raw.title, tags)

    # 3. Detect paywall
    paywalled = is_paywalled(raw.url)

    # 4. Create and store article
    article = Article(
        id=uuid.uuid4(),
        title=raw.title,
        author=raw.author,
        source_name=raw.source_name,
        url=raw.url,
        is_paywalled=paywalled,
        published_at=raw.published_at,
        ingested_at=datetime.now(timezone.utc),
        relevance_score=0.0,
        raw_tags=raw.raw_tags or [],
        matched_tags=matched,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)

    # 5. Publish to Redis
    await publish_article({
        "id": str(article.id),
        "title": article.title,
        "author": article.author,
        "source_name": article.source_name,
        "url": article.url,
        "is_paywalled": article.is_paywalled,
        "published_at": article.published_at.isoformat(),
        "ingested_at": article.ingested_at.isoformat(),
        "relevance_score": article.relevance_score,
        "matched_tags": article.matched_tags,
    })

    return article
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_pipeline.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/workers/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: add shared ingestion pipeline with dedupe, tagging, and paywall detection"
```

---

### Task 8: RSS Agent

**Files:**
- Create: `backend/src/workers/agents/rss.py`
- Create: `backend/tests/test_rss_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rss_agent.py
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from src.workers.agents.rss import RSSAgent, parse_feed_entries


def _make_feed_entry(title, link, author=None, published=None):
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.get = lambda key, default=None: {
        "author": author,
        "tags": [],
    }.get(key, default)
    entry.author = author
    entry.tags = []
    if published:
        entry.published_parsed = published
    else:
        entry.published_parsed = None
    return entry


def test_parse_feed_entries():
    entries = [
        _make_feed_entry("Article One", "https://example.com/1", author="Alice"),
        _make_feed_entry("Article Two", "https://example.com/2"),
    ]
    raw_articles = parse_feed_entries(entries, source_name="TestFeed")

    assert len(raw_articles) == 2
    assert raw_articles[0].title == "Article One"
    assert raw_articles[0].author == "Alice"
    assert raw_articles[0].source_name == "TestFeed"
    assert raw_articles[0].url == "https://example.com/1"
    assert raw_articles[1].author is None


def test_parse_feed_entries_skips_missing_title():
    entries = [
        _make_feed_entry(None, "https://example.com/no-title"),
        _make_feed_entry("Valid", "https://example.com/valid"),
    ]
    raw_articles = parse_feed_entries(entries, source_name="TestFeed")
    assert len(raw_articles) == 1
    assert raw_articles[0].title == "Valid"


def test_parse_feed_entries_skips_missing_link():
    entries = [
        _make_feed_entry("No Link", None),
        _make_feed_entry("Valid", "https://example.com/valid"),
    ]
    raw_articles = parse_feed_entries(entries, source_name="TestFeed")
    assert len(raw_articles) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_rss_agent.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement rss.py**

```python
# backend/src/workers/agents/rss.py
import logging
from calendar import timegm
from datetime import datetime, timezone
from time import mktime

import feedparser
import httpx

from src.workers.pipeline import RawArticle

logger = logging.getLogger(__name__)


def parse_feed_entries(entries: list, source_name: str) -> list[RawArticle]:
    """Convert feedparser entries into RawArticle objects."""
    articles = []
    for entry in entries:
        title = getattr(entry, "title", None)
        link = getattr(entry, "link", None)
        if not title or not link:
            continue

        author = getattr(entry, "author", None)

        # Parse published date
        published_at = datetime.now(timezone.utc)
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime.fromtimestamp(
                    timegm(entry.published_parsed), tz=timezone.utc
                )
            except (TypeError, ValueError, OverflowError):
                pass

        # Extract tags from feed entry
        raw_tags = []
        if hasattr(entry, "tags") and entry.tags:
            for tag in entry.tags:
                term = getattr(tag, "term", None)
                if term:
                    raw_tags.append(term)

        articles.append(RawArticle(
            title=title,
            author=author,
            source_name=source_name,
            url=link,
            published_at=published_at,
            raw_tags=raw_tags,
        ))
    return articles


class RSSAgent:
    """Fetches and parses RSS/Atom feeds."""

    def __init__(self):
        self._etags: dict[str, str] = {}  # feed_url -> etag
        self._modified: dict[str, str] = {}  # feed_url -> last-modified

    async def fetch_feed(self, feed_url: str, source_name: str) -> list[RawArticle]:
        """Fetch a single RSS feed and return parsed articles."""
        try:
            headers = {}
            if feed_url in self._etags:
                headers["If-None-Match"] = self._etags[feed_url]
            if feed_url in self._modified:
                headers["If-Modified-Since"] = self._modified[feed_url]

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(feed_url, headers=headers, follow_redirects=True)

            if resp.status_code == 304:
                logger.debug(f"Feed not modified: {source_name}")
                return []

            # Store cache headers for next request
            if "etag" in resp.headers:
                self._etags[feed_url] = resp.headers["etag"]
            if "last-modified" in resp.headers:
                self._modified[feed_url] = resp.headers["last-modified"]

            feed = feedparser.parse(resp.text)
            if feed.bozo and not feed.entries:
                logger.warning(f"Failed to parse feed from {source_name}: {feed.bozo_exception}")
                return []

            return parse_feed_entries(feed.entries, source_name)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {source_name}: {e}")
            return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_rss_agent.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/workers/agents/rss.py backend/tests/test_rss_agent.py
git commit -m "feat: add RSS agent with ETag caching and feed parsing"
```

---

### Task 9: News API Agent

**Files:**
- Create: `backend/src/workers/agents/newsapi.py`
- Create: `backend/tests/test_newsapi_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_newsapi_agent.py
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from src.workers.agents.newsapi import NewsAPIAgent, parse_newsapi_response


def test_parse_newsapi_response():
    response_data = {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "title": "AI Takes Over",
                "author": "Alice",
                "source": {"name": "TechCrunch"},
                "url": "https://techcrunch.com/ai",
                "publishedAt": "2026-04-10T10:00:00Z",
            },
            {
                "title": "Oil Prices Surge",
                "author": None,
                "source": {"name": "Reuters"},
                "url": "https://reuters.com/oil",
                "publishedAt": "2026-04-10T09:00:00Z",
            },
        ],
    }
    articles = parse_newsapi_response(response_data)
    assert len(articles) == 2
    assert articles[0].title == "AI Takes Over"
    assert articles[0].author == "Alice"
    assert articles[0].source_name == "TechCrunch"
    assert articles[1].author is None


def test_parse_newsapi_response_skips_removed():
    """NewsAPI returns '[Removed]' for DMCA'd articles."""
    response_data = {
        "status": "ok",
        "articles": [
            {
                "title": "[Removed]",
                "author": None,
                "source": {"name": "Unknown"},
                "url": "https://removed.example.com",
                "publishedAt": "2026-04-10T10:00:00Z",
            },
            {
                "title": "Valid Article",
                "author": "Bob",
                "source": {"name": "BBC"},
                "url": "https://bbc.com/valid",
                "publishedAt": "2026-04-10T09:00:00Z",
            },
        ],
    }
    articles = parse_newsapi_response(response_data)
    assert len(articles) == 1
    assert articles[0].title == "Valid Article"


def test_parse_newsapi_response_error_status():
    response_data = {"status": "error", "message": "rate limited"}
    articles = parse_newsapi_response(response_data)
    assert articles == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_newsapi_agent.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement newsapi.py**

```python
# backend/src/workers/agents/newsapi.py
import logging
from datetime import datetime, timezone

import httpx

from src.config import settings
from src.workers.pipeline import RawArticle

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"


def parse_newsapi_response(data: dict) -> list[RawArticle]:
    """Parse a NewsAPI response into RawArticle objects."""
    if data.get("status") != "ok":
        logger.warning(f"NewsAPI error: {data.get('message', 'unknown')}")
        return []

    articles = []
    for item in data.get("articles", []):
        title = item.get("title")
        url = item.get("url")
        if not title or not url or title == "[Removed]":
            continue

        published_at = datetime.now(timezone.utc)
        if item.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(
                    item["publishedAt"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        articles.append(RawArticle(
            title=title,
            author=item.get("author"),
            source_name=item.get("source", {}).get("name", "Unknown"),
            url=url,
            published_at=published_at,
            raw_tags=[],
        ))
    return articles


class NewsAPIAgent:
    """Fetches articles from NewsAPI.org."""

    async def fetch_top_headlines(self, country: str = "us") -> list[RawArticle]:
        """Fetch top headlines."""
        if not settings.newsapi_key:
            logger.warning("NEWSAPI_KEY not set, skipping NewsAPI agent")
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{NEWSAPI_BASE}/top-headlines",
                    params={"country": country, "pageSize": 100},
                    headers={"X-Api-Key": settings.newsapi_key},
                )
                resp.raise_for_status()
                return parse_newsapi_response(resp.json())
        except httpx.HTTPError as e:
            logger.error(f"NewsAPI HTTP error: {e}")
            return []

    async def fetch_by_query(self, query: str) -> list[RawArticle]:
        """Fetch articles matching a search query."""
        if not settings.newsapi_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{NEWSAPI_BASE}/everything",
                    params={"q": query, "sortBy": "publishedAt", "pageSize": 100},
                    headers={"X-Api-Key": settings.newsapi_key},
                )
                resp.raise_for_status()
                return parse_newsapi_response(resp.json())
        except httpx.HTTPError as e:
            logger.error(f"NewsAPI HTTP error: {e}")
            return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_newsapi_agent.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/workers/agents/newsapi.py backend/tests/test_newsapi_agent.py
git commit -m "feat: add NewsAPI agent with headline and query fetching"
```

---

### Task 10: Scraper Agent

**Files:**
- Create: `backend/src/workers/agents/scraper.py`
- Create: `backend/tests/test_scraper_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_scraper_agent.py
from src.workers.agents.scraper import parse_html_articles


SAMPLE_HTML = """
<html>
<body>
<article>
    <h2 class="title"><a href="https://example.com/article-1">Breaking News Story</a></h2>
    <span class="author">John Smith</span>
    <time datetime="2026-04-10T08:00:00Z">April 10, 2026</time>
</article>
<article>
    <h2 class="title"><a href="https://example.com/article-2">Another Story</a></h2>
    <span class="author">Jane Doe</span>
    <time datetime="2026-04-10T07:00:00Z">April 10, 2026</time>
</article>
</body>
</html>
"""


def test_parse_html_articles():
    config = {
        "article_selector": "article",
        "title_selector": "h2.title a",
        "link_selector": "h2.title a",
        "link_attr": "href",
        "author_selector": "span.author",
        "time_selector": "time",
        "time_attr": "datetime",
    }
    articles = parse_html_articles(SAMPLE_HTML, config, source_name="ExampleNews")
    assert len(articles) == 2
    assert articles[0].title == "Breaking News Story"
    assert articles[0].url == "https://example.com/article-1"
    assert articles[0].author == "John Smith"
    assert articles[0].source_name == "ExampleNews"


def test_parse_html_handles_missing_fields():
    html = """
    <html><body>
    <article>
        <h2 class="title"><a href="https://example.com/a1">Title Only</a></h2>
    </article>
    </body></html>
    """
    config = {
        "article_selector": "article",
        "title_selector": "h2.title a",
        "link_selector": "h2.title a",
        "link_attr": "href",
        "author_selector": "span.author",
        "time_selector": "time",
        "time_attr": "datetime",
    }
    articles = parse_html_articles(html, config, source_name="Test")
    assert len(articles) == 1
    assert articles[0].title == "Title Only"
    assert articles[0].author is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_scraper_agent.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement scraper.py**

```python
# backend/src/workers/agents/scraper.py
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.workers.pipeline import RawArticle

logger = logging.getLogger(__name__)


def parse_html_articles(
    html: str, config: dict, source_name: str
) -> list[RawArticle]:
    """Parse articles from HTML using CSS selectors defined in config.

    Config keys:
        article_selector: CSS selector for article containers
        title_selector: selector for title element (within article)
        link_selector: selector for link element (within article)
        link_attr: attribute on link element to extract URL from (default 'href')
        author_selector: selector for author element
        time_selector: selector for time element
        time_attr: attribute on time element for ISO datetime
    """
    soup = BeautifulSoup(html, "lxml")
    articles = []

    for container in soup.select(config["article_selector"]):
        # Title
        title_el = container.select_one(config.get("title_selector", ""))
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        # Link
        link_el = container.select_one(config.get("link_selector", ""))
        if not link_el:
            continue
        url = link_el.get(config.get("link_attr", "href"))
        if not url:
            continue

        # Author (optional)
        author = None
        author_el = container.select_one(config.get("author_selector", ""))
        if author_el:
            author = author_el.get_text(strip=True) or None

        # Published time (optional)
        published_at = datetime.now(timezone.utc)
        time_el = container.select_one(config.get("time_selector", ""))
        if time_el:
            time_str = time_el.get(config.get("time_attr", "datetime"), "")
            if time_str:
                try:
                    published_at = datetime.fromisoformat(
                        time_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

        articles.append(RawArticle(
            title=title,
            author=author,
            source_name=source_name,
            url=url,
            published_at=published_at,
            raw_tags=[],
        ))

    return articles


class ScraperAgent:
    """Scrapes news articles from web pages using per-source CSS selectors."""

    async def fetch_page(
        self, page_url: str, config: dict, source_name: str
    ) -> list[RawArticle]:
        """Fetch a page and parse articles from it."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(page_url, follow_redirects=True)
                resp.raise_for_status()
            return parse_html_articles(resp.text, config, source_name)
        except httpx.HTTPError as e:
            logger.error(f"Scraper HTTP error for {source_name}: {e}")
            return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_scraper_agent.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/workers/agents/scraper.py backend/tests/test_scraper_agent.py
git commit -m "feat: add scraper agent with CSS selector-based HTML parsing"
```

---

### Task 11: Ranker

**Files:**
- Create: `backend/src/workers/ranker.py`
- Create: `backend/tests/test_ranker.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ranker.py
import math
from datetime import datetime, timezone, timedelta
from src.workers.ranker import compute_relevance_score


def test_high_tag_match_high_authority():
    score = compute_relevance_score(
        matched_tag_count=3,
        max_possible_tags=4,
        tag_priority_sum=3,
        max_priority_sum=4,
        source_authority=1.0,
        article_age_hours=0.5,
    )
    assert score > 0.8


def test_no_tags_low_authority_old():
    score = compute_relevance_score(
        matched_tag_count=0,
        max_possible_tags=4,
        tag_priority_sum=0,
        max_priority_sum=4,
        source_authority=0.2,
        article_age_hours=48.0,
    )
    assert score < 0.2


def test_recency_matters():
    recent = compute_relevance_score(
        matched_tag_count=1,
        max_possible_tags=4,
        tag_priority_sum=1,
        max_priority_sum=4,
        source_authority=0.5,
        article_age_hours=0.1,
    )
    old = compute_relevance_score(
        matched_tag_count=1,
        max_possible_tags=4,
        tag_priority_sum=1,
        max_priority_sum=4,
        source_authority=0.5,
        article_age_hours=24.0,
    )
    assert recent > old


def test_score_between_0_and_1():
    score = compute_relevance_score(
        matched_tag_count=2,
        max_possible_tags=5,
        tag_priority_sum=2,
        max_priority_sum=5,
        source_authority=0.7,
        article_age_hours=6.0,
    )
    assert 0.0 <= score <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_ranker.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement ranker.py**

```python
# backend/src/workers/ranker.py
import logging
import math
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Article, Tag, Source

logger = logging.getLogger(__name__)

# Weights
W_TAG = 0.5
W_AUTHORITY = 0.3
W_RECENCY = 0.2

# Recency half-life in hours — score halves every 6 hours
HALF_LIFE_HOURS = 6.0


def compute_relevance_score(
    matched_tag_count: int,
    max_possible_tags: int,
    tag_priority_sum: int,
    max_priority_sum: int,
    source_authority: float,
    article_age_hours: float,
) -> float:
    """Compute relevance score between 0 and 1.

    score = (tag_relevance * 0.5) + (source_authority * 0.3) + (recency * 0.2)
    """
    # Tag relevance: combine count ratio and priority ratio
    if max_possible_tags > 0 and max_priority_sum > 0:
        count_ratio = matched_tag_count / max_possible_tags
        priority_ratio = tag_priority_sum / max_priority_sum
        tag_relevance = (count_ratio + priority_ratio) / 2
    else:
        tag_relevance = 0.0

    # Recency: exponential decay
    decay = math.exp(-math.log(2) * article_age_hours / HALF_LIFE_HOURS)
    recency = max(0.0, min(1.0, decay))

    # Clamp authority
    authority = max(0.0, min(1.0, source_authority))

    score = (W_TAG * tag_relevance) + (W_AUTHORITY * authority) + (W_RECENCY * recency)
    return max(0.0, min(1.0, score))


async def run_ranker(session: AsyncSession) -> int:
    """Recompute relevance_score for all articles from the last 48 hours.

    Returns the number of articles updated.
    """
    # Load active tags for max calculations
    tag_result = await session.execute(select(Tag).where(Tag.active.is_(True)))
    tags = list(tag_result.scalars())
    max_possible_tags = len(tags)
    max_priority_sum = sum(t.priority for t in tags) if tags else 1
    tag_priority_map = {t.name: t.priority for t in tags}

    # Load source authority map
    source_result = await session.execute(select(Source))
    source_authority_map = {s.name: s.authority_score for s in source_result.scalars()}

    # Load recent articles (last 48 hours)
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    article_result = await session.execute(
        select(Article).where(Article.ingested_at >= cutoff)
    )
    articles = list(article_result.scalars())

    now = datetime.now(timezone.utc)
    updated = 0
    for article in articles:
        tag_priority_sum = sum(
            tag_priority_map.get(t, 0) for t in (article.matched_tags or [])
        )
        age_hours = (now - article.ingested_at).total_seconds() / 3600

        new_score = compute_relevance_score(
            matched_tag_count=len(article.matched_tags or []),
            max_possible_tags=max_possible_tags,
            tag_priority_sum=tag_priority_sum,
            max_priority_sum=max_priority_sum,
            source_authority=source_authority_map.get(article.source_name, 0.5),
            article_age_hours=age_hours,
        )

        if article.relevance_score != new_score:
            article.relevance_score = new_score
            updated += 1

    await session.commit()
    logger.info(f"Ranker updated {updated}/{len(articles)} articles")
    return updated
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_ranker.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/workers/ranker.py backend/tests/test_ranker.py
git commit -m "feat: add ranker with tag relevance, source authority, and recency scoring"
```

---

### Task 12: API Routes — Articles

**Files:**
- Create: `backend/src/api/routes/articles.py`
- Create: `backend/tests/test_api_articles.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api_articles.py
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
    """Create FastAPI app with test session override."""
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
    # Should be sorted by relevance_score descending
    scores = [a["relevance_score"] for a in data]
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api_articles.py -v
```

Expected: FAIL — modules don't exist

- [ ] **Step 3: Create the FastAPI app skeleton**

```python
# backend/src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import articles, tags, sources


def create_app() -> FastAPI:
    app = FastAPI(title="Stream News API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tauri app connects from localhost
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(articles.router)
    app.include_router(tags.router)
    app.include_router(sources.router)

    return app
```

- [ ] **Step 4: Implement articles routes**

```python
# backend/src/api/routes/articles.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models import Article

router = APIRouter()


@router.get("/articles")
async def list_articles(
    tag: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    query = select(Article).order_by(Article.ingested_at.desc())
    if tag:
        query = query.where(Article.matched_tags.any(tag))
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    articles = result.scalars().all()
    return [_serialize(a) for a in articles]


@router.get("/articles/top")
async def top_articles(
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_session),
):
    query = (
        select(Article)
        .order_by(Article.relevance_score.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    articles = result.scalars().all()
    return [_serialize(a) for a in articles]


def _serialize(article: Article) -> dict:
    return {
        "id": str(article.id),
        "title": article.title,
        "author": article.author,
        "source_name": article.source_name,
        "url": article.url,
        "is_paywalled": article.is_paywalled,
        "published_at": article.published_at.isoformat(),
        "ingested_at": article.ingested_at.isoformat(),
        "relevance_score": article.relevance_score,
        "matched_tags": article.matched_tags,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_api_articles.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/main.py backend/src/api/routes/articles.py backend/tests/test_api_articles.py
git commit -m "feat: add articles REST endpoints with tag filtering and top ranking"
```

---

### Task 13: API Routes — Tags

**Files:**
- Create: `backend/src/api/routes/tags.py`
- Create: `backend/tests/test_api_tags.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api_tags.py
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.db import get_session


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


async def test_create_tag(client):
    resp = await client.post("/tags", json={
        "name": "technology",
        "keywords": ["tech", "AI", "software"],
        "priority": 1,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "technology"
    assert data["keywords"] == ["tech", "AI", "software"]
    assert data["active"] is True


async def test_list_tags(client):
    await client.post("/tags", json={"name": "tech", "keywords": ["tech"], "priority": 1})
    await client.post("/tags", json={"name": "oil", "keywords": ["oil"], "priority": 2})

    resp = await client.get("/tags")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_tag(client):
    create_resp = await client.post("/tags", json={"name": "tech", "keywords": ["tech"], "priority": 1})
    tag_id = create_resp.json()["id"]

    resp = await client.put(f"/tags/{tag_id}", json={
        "keywords": ["tech", "AI", "ML"],
        "priority": 3,
    })
    assert resp.status_code == 200
    assert resp.json()["keywords"] == ["tech", "AI", "ML"]
    assert resp.json()["priority"] == 3


async def test_delete_tag(client):
    create_resp = await client.post("/tags", json={"name": "temp", "keywords": ["temp"], "priority": 1})
    tag_id = create_resp.json()["id"]

    resp = await client.delete(f"/tags/{tag_id}")
    assert resp.status_code == 204

    list_resp = await client.get("/tags")
    assert len(list_resp.json()) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api_tags.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement tags routes**

```python
# backend/src/api/routes/tags.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models import Tag

router = APIRouter()


class TagCreate(BaseModel):
    name: str
    keywords: list[str]
    priority: int = 1


class TagUpdate(BaseModel):
    name: str | None = None
    keywords: list[str] | None = None
    priority: int | None = None
    active: bool | None = None


@router.get("/tags")
async def list_tags(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Tag).order_by(Tag.name))
    return [_serialize(t) for t in result.scalars()]


@router.post("/tags", status_code=201)
async def create_tag(body: TagCreate, session: AsyncSession = Depends(get_session)):
    tag = Tag(
        id=uuid.uuid4(),
        name=body.name,
        keywords=body.keywords,
        priority=body.priority,
        active=True,
    )
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return _serialize(tag)


@router.put("/tags/{tag_id}")
async def update_tag(
    tag_id: str,
    body: TagUpdate,
    session: AsyncSession = Depends(get_session),
):
    tag = await session.get(Tag, uuid.UUID(tag_id))
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if body.name is not None:
        tag.name = body.name
    if body.keywords is not None:
        tag.keywords = body.keywords
    if body.priority is not None:
        tag.priority = body.priority
    if body.active is not None:
        tag.active = body.active

    await session.commit()
    await session.refresh(tag)
    return _serialize(tag)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: str,
    session: AsyncSession = Depends(get_session),
):
    tag = await session.get(Tag, uuid.UUID(tag_id))
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    await session.delete(tag)
    await session.commit()


def _serialize(tag: Tag) -> dict:
    return {
        "id": str(tag.id),
        "name": tag.name,
        "keywords": tag.keywords,
        "priority": tag.priority,
        "active": tag.active,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_api_tags.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/routes/tags.py backend/tests/test_api_tags.py
git commit -m "feat: add tags CRUD REST endpoints"
```

---

### Task 14: API Routes — Sources

**Files:**
- Create: `backend/src/api/routes/sources.py`
- Create: `backend/tests/test_api_sources.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api_sources.py
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.db import get_session


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


async def test_create_source(client):
    resp = await client.post("/sources", json={
        "name": "Reuters",
        "type": "rss",
        "config": {"feed_url": "https://feeds.reuters.com/reuters/topNews"},
        "authority_score": 1.0,
        "poll_interval": 60,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Reuters"
    assert data["type"] == "rss"
    assert data["active"] is True


async def test_list_sources(client):
    await client.post("/sources", json={
        "name": "Reuters", "type": "rss",
        "config": {"feed_url": "https://example.com/feed"}, "authority_score": 1.0, "poll_interval": 60,
    })
    await client.post("/sources", json={
        "name": "BBC", "type": "rss",
        "config": {"feed_url": "https://example.com/bbc"}, "authority_score": 0.9, "poll_interval": 60,
    })

    resp = await client.get("/sources")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api_sources.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement sources routes**

```python
# backend/src/api/routes/sources.py
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models import Source

router = APIRouter()


class SourceCreate(BaseModel):
    name: str
    type: str  # rss, api, scraper
    config: dict
    authority_score: float = 0.5
    poll_interval: int = 60


@router.get("/sources")
async def list_sources(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Source).order_by(Source.name))
    return [_serialize(s) for s in result.scalars()]


@router.post("/sources", status_code=201)
async def create_source(body: SourceCreate, session: AsyncSession = Depends(get_session)):
    source = Source(
        id=uuid.uuid4(),
        name=body.name,
        type=body.type,
        config=body.config,
        authority_score=body.authority_score,
        poll_interval=body.poll_interval,
        active=True,
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return _serialize(source)


def _serialize(source: Source) -> dict:
    return {
        "id": str(source.id),
        "name": source.name,
        "type": source.type,
        "config": source.config,
        "authority_score": source.authority_score,
        "poll_interval": source.poll_interval,
        "active": source.active,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_api_sources.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/routes/sources.py backend/tests/test_api_sources.py
git commit -m "feat: add sources list and create REST endpoints"
```

---

### Task 15: WebSocket Endpoint

**Files:**
- Create: `backend/src/api/websocket.py`
- Create: `backend/tests/test_websocket.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_websocket.py
import json
import pytest
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.main import create_app
from src.db import get_session


@pytest.fixture
def app(session):
    application = create_app()

    async def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    return application


def test_websocket_connects(app):
    """Test that WebSocket endpoint accepts connections."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        # Send a ping, expect a pong
        ws.send_json({"type": "ping"})
        data = ws.receive_json()
        assert data["type"] == "pong"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_websocket.py -v
```

Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement websocket.py**

```python
# backend/src/api/websocket.py
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.redis_pubsub import subscribe_articles

logger = logging.getLogger(__name__)
router = APIRouter()

# Track connected clients
connected_clients: set[WebSocket] = set()


async def broadcast(message: dict):
    """Send a message to all connected WebSocket clients."""
    dead = set()
    for ws in connected_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)


async def redis_listener():
    """Background task: subscribe to Redis and broadcast new articles."""
    try:
        async for article_data in subscribe_articles():
            await broadcast({"type": "new_article", "data": article_data})
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Redis listener error: {e}")


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)
    logger.info(f"Client connected. Total: {len(connected_clients)}")
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(ws)
        logger.info(f"Client disconnected. Total: {len(connected_clients)}")
```

- [ ] **Step 4: Register WebSocket router in main.py**

Update `backend/src/api/main.py` — add the websocket router and Redis listener startup:

```python
# backend/src/api/main.py
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import articles, tags, sources
from src.api import websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Redis listener on startup
    task = asyncio.create_task(websocket.redis_listener())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="Stream News API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(articles.router)
    app.include_router(tags.router)
    app.include_router(sources.router)
    app.include_router(websocket.router)

    return app
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_websocket.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/websocket.py backend/src/api/main.py backend/tests/test_websocket.py
git commit -m "feat: add WebSocket endpoint with Redis pub/sub broadcast"
```

---

### Task 16: Worker Entry Point

**Files:**
- Create: `backend/src/workers/main.py`

- [ ] **Step 1: Implement the worker orchestrator**

```python
# backend/src/workers/main.py
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import async_session
from src.models import Source
from src.workers.agents.rss import RSSAgent
from src.workers.agents.newsapi import NewsAPIAgent
from src.workers.agents.scraper import ScraperAgent
from src.workers.pipeline import ingest_article
from src.workers.ranker import run_ranker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

rss_agent = RSSAgent()
newsapi_agent = NewsAPIAgent()
scraper_agent = ScraperAgent()


async def run_rss_sources():
    """Fetch all active RSS sources and ingest articles."""
    async with async_session() as session:
        result = await session.execute(
            select(Source).where(Source.type == "rss", Source.active.is_(True))
        )
        sources = list(result.scalars())

    for source in sources:
        feed_url = source.config.get("feed_url")
        if not feed_url:
            continue

        raw_articles = await rss_agent.fetch_feed(feed_url, source.name)
        async with async_session() as session:
            count = 0
            for raw in raw_articles:
                result = await ingest_article(raw, session)
                if result:
                    count += 1
        if count > 0:
            logger.info(f"RSS [{source.name}]: ingested {count} new articles")


async def run_newsapi_sources():
    """Fetch from NewsAPI."""
    raw_articles = await newsapi_agent.fetch_top_headlines()
    async with async_session() as session:
        count = 0
        for raw in raw_articles:
            result = await ingest_article(raw, session)
            if result:
                count += 1
    if count > 0:
        logger.info(f"NewsAPI: ingested {count} new articles")


async def run_scraper_sources():
    """Fetch all active scraper sources and ingest articles."""
    async with async_session() as session:
        result = await session.execute(
            select(Source).where(Source.type == "scraper", Source.active.is_(True))
        )
        sources = list(result.scalars())

    for source in sources:
        page_url = source.config.get("page_url")
        if not page_url:
            continue

        raw_articles = await scraper_agent.fetch_page(page_url, source.config, source.name)
        async with async_session() as session:
            count = 0
            for raw in raw_articles:
                result = await ingest_article(raw, session)
                if result:
                    count += 1
        if count > 0:
            logger.info(f"Scraper [{source.name}]: ingested {count} new articles")


async def run_ranking():
    """Run the ranker."""
    async with async_session() as session:
        await run_ranker(session)


async def periodic(coro_fn, interval_seconds: int, name: str):
    """Run a coroutine function repeatedly at a fixed interval."""
    while True:
        try:
            await coro_fn()
        except Exception as e:
            logger.error(f"{name} error: {e}", exc_info=True)
        await asyncio.sleep(interval_seconds)


async def main():
    logger.info("Stream worker starting...")

    await asyncio.gather(
        periodic(run_rss_sources, 60, "RSS"),
        periodic(run_newsapi_sources, 300, "NewsAPI"),
        periodic(run_scraper_sources, 120, "Scraper"),
        periodic(run_ranking, 60, "Ranker"),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify it imports correctly**

```bash
cd backend && python -c "from src.workers.main import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/src/workers/main.py
git commit -m "feat: add worker entry point with periodic RSS, API, scraper, and ranker tasks"
```

---

### Task 17: Seed Data

**Files:**
- Create: `backend/src/seed.py`

- [ ] **Step 1: Implement seed script**

```python
# backend/src/seed.py
"""Seed the database with initial tags and RSS sources."""
import asyncio
import uuid

from sqlalchemy import select

from src.db import async_session
from src.models import Tag, Source

INITIAL_TAGS = [
    {"name": "technology", "keywords": ["tech", "AI", "software", "hardware", "startup", "silicon valley", "computing", "machine learning", "cybersecurity"], "priority": 1},
    {"name": "sustainability", "keywords": ["climate", "renewable", "green energy", "carbon", "ESG", "environmental", "solar", "wind power", "emissions"], "priority": 1},
    {"name": "oil", "keywords": ["oil", "petroleum", "OPEC", "crude", "natural gas", "drilling", "refinery", "pipeline", "fossil fuel"], "priority": 1},
    {"name": "politics", "keywords": ["election", "congress", "senate", "policy", "legislation", "government", "geopolitics", "diplomacy", "white house"], "priority": 1},
]

INITIAL_SOURCES = [
    # --- RSS Sources (verified April 2026) ---
    # NOTE: Reuters killed all RSS in 2020 — use Google News proxy
    {"name": "Reuters (via Google News)", "type": "rss", "config": {"feed_url": "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US"}, "authority_score": 1.0, "poll_interval": 120},
    {"name": "AP News", "type": "rss", "config": {"feed_url": "https://apnews.com/hub/ap-top-news.rss"}, "authority_score": 1.0, "poll_interval": 60},
    {"name": "AP Politics", "type": "rss", "config": {"feed_url": "https://apnews.com/politics.rss"}, "authority_score": 1.0, "poll_interval": 120},
    {"name": "AP Technology", "type": "rss", "config": {"feed_url": "https://apnews.com/technology.rss"}, "authority_score": 1.0, "poll_interval": 120},
    {"name": "BBC News", "type": "rss", "config": {"feed_url": "https://feeds.bbci.co.uk/news/rss.xml"}, "authority_score": 0.95, "poll_interval": 60},
    {"name": "BBC Technology", "type": "rss", "config": {"feed_url": "https://feeds.bbci.co.uk/news/technology/rss.xml"}, "authority_score": 0.95, "poll_interval": 120},
    {"name": "BBC Science & Environment", "type": "rss", "config": {"feed_url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"}, "authority_score": 0.95, "poll_interval": 120},
    {"name": "TechCrunch", "type": "rss", "config": {"feed_url": "https://techcrunch.com/feed/"}, "authority_score": 0.8, "poll_interval": 60},
    {"name": "TechCrunch AI", "type": "rss", "config": {"feed_url": "https://techcrunch.com/category/artificial-intelligence/feed/"}, "authority_score": 0.8, "poll_interval": 120},
    {"name": "Ars Technica", "type": "rss", "config": {"feed_url": "https://feeds.arstechnica.com/arstechnica/index"}, "authority_score": 0.8, "poll_interval": 120},
    {"name": "The Verge", "type": "rss", "config": {"feed_url": "https://www.theverge.com/rss/index.xml"}, "authority_score": 0.75, "poll_interval": 120},
    {"name": "The Guardian - World", "type": "rss", "config": {"feed_url": "https://www.theguardian.com/world/rss"}, "authority_score": 0.9, "poll_interval": 60},
    {"name": "The Guardian - Environment", "type": "rss", "config": {"feed_url": "https://www.theguardian.com/environment/rss"}, "authority_score": 0.9, "poll_interval": 120},
    {"name": "The Guardian - Technology", "type": "rss", "config": {"feed_url": "https://www.theguardian.com/technology/rss"}, "authority_score": 0.9, "poll_interval": 120},
    {"name": "The Guardian - US Politics", "type": "rss", "config": {"feed_url": "https://www.theguardian.com/us-news/us-politics/rss"}, "authority_score": 0.9, "poll_interval": 120},
    {"name": "CNBC Top News", "type": "rss", "config": {"feed_url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"}, "authority_score": 0.85, "poll_interval": 60},
    {"name": "CNBC Energy", "type": "rss", "config": {"feed_url": "https://www.cnbc.com/id/19836768/device/rss/rss.html"}, "authority_score": 0.85, "poll_interval": 120},
    {"name": "CNBC Technology", "type": "rss", "config": {"feed_url": "https://www.cnbc.com/id/19854910/device/rss/rss.html"}, "authority_score": 0.85, "poll_interval": 120},
    {"name": "CNBC Politics", "type": "rss", "config": {"feed_url": "https://www.cnbc.com/id/10000113/device/rss/rss.html"}, "authority_score": 0.85, "poll_interval": 120},
    {"name": "Politico - Politics", "type": "rss", "config": {"feed_url": "https://rss.politico.com/politics-news.xml"}, "authority_score": 0.85, "poll_interval": 120},
    {"name": "Politico - Energy", "type": "rss", "config": {"feed_url": "https://rss.politico.com/energy.xml"}, "authority_score": 0.85, "poll_interval": 120},
    {"name": "Politico - Congress", "type": "rss", "config": {"feed_url": "https://rss.politico.com/congress.xml"}, "authority_score": 0.85, "poll_interval": 120},
    {"name": "OilPrice.com", "type": "rss", "config": {"feed_url": "https://oilprice.com/rss/main"}, "authority_score": 0.7, "poll_interval": 120},
    {"name": "OilPrice - Geopolitics", "type": "rss", "config": {"feed_url": "https://oilprice.com/rss/category/geopolitics"}, "authority_score": 0.7, "poll_interval": 120},
    {"name": "Hacker News", "type": "rss", "config": {"feed_url": "https://hnrss.org/frontpage"}, "authority_score": 0.7, "poll_interval": 120},
    {"name": "E&E News", "type": "rss", "config": {"feed_url": "https://www.eenews.net/articles/feed/"}, "authority_score": 0.75, "poll_interval": 180},
    {"name": "NPR News", "type": "rss", "config": {"feed_url": "https://feeds.npr.org/1001/rss.xml"}, "authority_score": 0.85, "poll_interval": 120},
    {"name": "Al Jazeera", "type": "rss", "config": {"feed_url": "https://www.aljazeera.com/xml/rss/all.xml"}, "authority_score": 0.8, "poll_interval": 120},
]


async def seed():
    async with async_session() as session:
        # Seed tags
        for tag_data in INITIAL_TAGS:
            exists = await session.execute(
                select(Tag).where(Tag.name == tag_data["name"])
            )
            if exists.scalar_one_or_none() is None:
                session.add(Tag(id=uuid.uuid4(), active=True, **tag_data))
                print(f"  + Tag: {tag_data['name']}")

        # Seed sources
        for src_data in INITIAL_SOURCES:
            exists = await session.execute(
                select(Source).where(Source.name == src_data["name"])
            )
            if exists.scalar_one_or_none() is None:
                session.add(Source(id=uuid.uuid4(), active=True, **src_data))
                print(f"  + Source: {src_data['name']}")

        await session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Verify it imports**

```bash
cd backend && python -c "from src.seed import INITIAL_TAGS, INITIAL_SOURCES; print(f'{len(INITIAL_TAGS)} tags, {len(INITIAL_SOURCES)} sources')"
```

Expected: `4 tags, 28 sources`

- [ ] **Step 3: Commit**

```bash
git add backend/src/seed.py
git commit -m "feat: add seed script with initial tags and RSS sources"
```

---

### Task 18: Docker Compose + Deployment

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/docker-compose.yml`
- Create: `backend/nginx.conf`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic.ini .
COPY alembic/ alembic/

# API server
FROM base AS api
CMD ["uvicorn", "src.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# Worker
FROM base AS worker
CMD ["python", "-m", "src.workers.main"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# backend/docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: stream
      POSTGRES_PASSWORD: stream
      POSTGRES_DB: stream
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stream"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      target: api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://stream:stream@postgres:5432/stream
      REDIS_URL: redis://redis:6379/0
      NEWSAPI_KEY: ${NEWSAPI_KEY:-}
      GNEWS_API_KEY: ${GNEWS_API_KEY:-}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: .
      target: worker
    environment:
      DATABASE_URL: postgresql+asyncpg://stream:stream@postgres:5432/stream
      REDIS_URL: redis://redis:6379/0
      NEWSAPI_KEY: ${NEWSAPI_KEY:-}
      GNEWS_API_KEY: ${GNEWS_API_KEY:-}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - api

volumes:
  pgdata:
```

- [ ] **Step 3: Create nginx.conf**

```nginx
# backend/nginx.conf
upstream api {
    server api:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

- [ ] **Step 4: Test Docker Compose builds**

```bash
cd backend && docker compose build
```

Expected: both `api` and `worker` targets build successfully

- [ ] **Step 5: Test full stack starts**

```bash
cd backend && docker compose up -d
```

Wait for health checks, then:

```bash
docker compose ps
```

Expected: all services running/healthy

- [ ] **Step 6: Run migrations + seed inside Docker**

```bash
cd backend && docker compose exec api alembic upgrade head
cd backend && docker compose exec api python -m src.seed
```

- [ ] **Step 7: Verify API responds**

```bash
curl http://localhost/tags
```

Expected: JSON array of seeded tags

- [ ] **Step 8: Commit**

```bash
git add backend/Dockerfile backend/docker-compose.yml backend/nginx.conf
git commit -m "feat: add Docker Compose stack with Postgres, Redis, API, worker, and Nginx"
```

---

### Task 19: Integration Smoke Test

**Files:**
- Create: `backend/tests/test_integration.py`

- [ ] **Step 1: Write integration test**

This test requires Docker services running (Postgres + Redis).

```python
# backend/tests/test_integration.py
"""Integration smoke test — requires running Postgres and Redis."""
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.api.main import create_app
from src.db import get_session
from src.models import Base, Tag
from src.workers.pipeline import RawArticle, ingest_article
from src.workers.ranker import run_ranker

TEST_DB_URL = "postgresql+asyncpg://stream:stream@localhost:5432/stream_test"


@pytest.fixture
async def pg_engine():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def pg_session(pg_engine):
    factory = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def seeded_session(pg_session):
    """Add a tag so pipeline can match against it."""
    tag = Tag(id=uuid.uuid4(), name="technology", keywords=["AI", "tech"], priority=1, active=True)
    pg_session.add(tag)
    await pg_session.commit()
    return pg_session


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

    from unittest.mock import AsyncMock, patch
    with patch("src.workers.pipeline.publish_article", new_callable=AsyncMock):
        article = await ingest_article(raw, seeded_session)

    assert article is not None
    assert "technology" in article.matched_tags

    # Now query via API
    app = create_app()

    async def override():
        yield seeded_session

    app.dependency_overrides[get_session] = override

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
```

- [ ] **Step 2: Run integration test**

```bash
cd backend && docker compose exec postgres psql -U stream -c "CREATE DATABASE stream_test;" 2>/dev/null || true
cd backend && python -m pytest tests/test_integration.py -v
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_integration.py
git commit -m "test: add integration smoke test for pipeline → API → ranker flow"
```
