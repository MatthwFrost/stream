# backend/src/workers/pipeline.py
import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Article, Tag
from src.services.paywall import is_paywalled
from src.services.tag_matcher import match_tags
from src.services.redis_pubsub import publish_article

_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "over", "after",
    "says", "say", "said", "report", "reports", "reported", "exclusive",
    "breaking", "update", "updated", "new", "latest", "live", "just",
    "sources", "source", "according", "amid", "as", "its", "it", "is",
    "are", "was", "were", "has", "have", "had", "be", "been", "will",
    "would", "could", "should", "may", "might", "can", "that", "this",
    "their", "them", "they", "who", "what", "when", "where", "how", "why",
})

_TITLE_HASH_WINDOW_HOURS = 24
_TITLE_HASH_WORDS = 8


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, remove stop words, take first N meaningful words."""
    lowered = title.lower()
    words = re.findall(r"[a-z0-9]+", lowered)
    meaningful = [w for w in words if w not in _STOP_WORDS]
    return " ".join(meaningful[:_TITLE_HASH_WORDS])


def compute_title_hash(title: str) -> str:
    normalized = _normalize_title(title)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


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
    """
    # 1. Deduplicate by exact URL
    existing = await session.execute(select(Article).where(Article.url == raw.url))
    if existing.scalar_one_or_none() is not None:
        return None

    # 2. Deduplicate by title hash within 24h window (catches same story from multiple sources)
    title_hash = compute_title_hash(raw.title)
    window_start = datetime.now(timezone.utc) - timedelta(hours=_TITLE_HASH_WINDOW_HOURS)
    dup = await session.execute(
        select(Article).where(
            and_(
                Article.title_hash == title_hash,
                Article.ingested_at >= window_start,
            )
        )
    )
    if dup.scalar_one_or_none() is not None:
        return None

    # 3. Load active tags and match
    tag_rows = await session.execute(select(Tag).where(Tag.active.is_(True)))
    tags = [{"name": t.name, "keywords": t.keywords, "priority": t.priority} for t in tag_rows.scalars()]
    matched = match_tags(raw.title, tags)

    # 4. Detect paywall
    paywalled = is_paywalled(raw.url)

    # 5. Create and store article
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
        title_hash=title_hash,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)

    # 6. Publish to Redis
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
