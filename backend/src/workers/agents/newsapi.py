# backend/src/workers/agents/newsapi.py
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.workers.pipeline import RawArticle

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"


def parse_newsapi_response(data: dict) -> list[RawArticle]:
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
    async def fetch_top_headlines(self, session: AsyncSession, country: str = "us") -> list[RawArticle]:
        from src.services.config_store import get_api_key
        key = await get_api_key("newsapi_key", session)
        if not key:
            logger.warning("NEWSAPI_KEY not set, skipping NewsAPI agent")
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{NEWSAPI_BASE}/top-headlines",
                    params={"country": country, "pageSize": 100},
                    headers={"X-Api-Key": key},
                )
                resp.raise_for_status()
                return parse_newsapi_response(resp.json())
        except httpx.HTTPError as e:
            logger.error(f"NewsAPI HTTP error: {e}")
            return []

    async def fetch_by_query(self, query: str, session: AsyncSession) -> list[RawArticle]:
        from src.services.config_store import get_api_key
        key = await get_api_key("newsapi_key", session)
        if not key:
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{NEWSAPI_BASE}/everything",
                    params={"q": query, "sortBy": "publishedAt", "pageSize": 100},
                    headers={"X-Api-Key": key},
                )
                resp.raise_for_status()
                return parse_newsapi_response(resp.json())
        except httpx.HTTPError as e:
            logger.error(f"NewsAPI HTTP error: {e}")
            return []
