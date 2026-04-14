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
    result = await session.execute(query)
    articles = list(result.scalars().all())

    if tag:
        articles = [a for a in articles if tag in (a.matched_tags or [])]

    # Apply offset and limit after filtering
    articles = articles[offset:offset + limit]
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
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "ingested_at": article.ingested_at.isoformat() if article.ingested_at else None,
        "relevance_score": article.relevance_score,
        "matched_tags": article.matched_tags or [],
    }
