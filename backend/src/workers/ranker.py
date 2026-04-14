import logging
import math
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Article, Tag, Source

logger = logging.getLogger(__name__)

W_TAG = 0.5
W_AUTHORITY = 0.3
W_RECENCY = 0.2
HALF_LIFE_HOURS = 6.0


def compute_relevance_score(
    matched_tag_count: int,
    max_possible_tags: int,
    tag_priority_sum: int,
    max_priority_sum: int,
    source_authority: float,
    article_age_hours: float,
) -> float:
    if max_possible_tags > 0 and max_priority_sum > 0:
        count_ratio = matched_tag_count / max_possible_tags
        priority_ratio = tag_priority_sum / max_priority_sum
        tag_relevance = (count_ratio + priority_ratio) / 2
    else:
        tag_relevance = 0.0

    decay = math.exp(-math.log(2) * article_age_hours / HALF_LIFE_HOURS)
    recency = max(0.0, min(1.0, decay))
    authority = max(0.0, min(1.0, source_authority))

    score = (W_TAG * tag_relevance) + (W_AUTHORITY * authority) + (W_RECENCY * recency)
    return max(0.0, min(1.0, score))


async def run_ranker(session: AsyncSession) -> int:
    tag_result = await session.execute(select(Tag).where(Tag.active.is_(True)))
    tags = list(tag_result.scalars())
    max_possible_tags = len(tags)
    max_priority_sum = sum(t.priority for t in tags) if tags else 1
    tag_priority_map = {t.name: t.priority for t in tags}

    source_result = await session.execute(select(Source))
    source_authority_map = {s.name: s.authority_score for s in source_result.scalars()}

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
        ingested_at = article.ingested_at
        if ingested_at.tzinfo is None:
            ingested_at = ingested_at.replace(tzinfo=timezone.utc)
        age_hours = (now - ingested_at).total_seconds() / 3600

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
