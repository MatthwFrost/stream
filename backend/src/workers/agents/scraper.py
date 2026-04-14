# backend/src/workers/agents/scraper.py
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.workers.pipeline import RawArticle

logger = logging.getLogger(__name__)


def parse_html_articles(html: str, config: dict, source_name: str) -> list[RawArticle]:
    soup = BeautifulSoup(html, "lxml")
    articles = []

    for container in soup.select(config["article_selector"]):
        title_el = container.select_one(config.get("title_selector", ""))
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        link_el = container.select_one(config.get("link_selector", ""))
        if not link_el:
            continue
        url = link_el.get(config.get("link_attr", "href"))
        if not url:
            continue

        author = None
        author_el = container.select_one(config.get("author_selector", ""))
        if author_el:
            author = author_el.get_text(strip=True) or None

        published_at = datetime.now(timezone.utc)
        time_el = container.select_one(config.get("time_selector", ""))
        if time_el:
            time_str = time_el.get(config.get("time_attr", "datetime"), "")
            if time_str:
                try:
                    published_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
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
    async def fetch_page(self, page_url: str, config: dict, source_name: str) -> list[RawArticle]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(page_url, follow_redirects=True)
                resp.raise_for_status()
            return parse_html_articles(resp.text, config, source_name)
        except httpx.HTTPError as e:
            logger.error(f"Scraper HTTP error for {source_name}: {e}")
            return []
