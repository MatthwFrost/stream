# backend/src/workers/agents/rss.py
import logging
from calendar import timegm
from datetime import datetime, timezone

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

        published_at = datetime.now(timezone.utc)
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime.fromtimestamp(
                    timegm(entry.published_parsed), tz=timezone.utc
                )
            except (TypeError, ValueError, OverflowError):
                pass

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
        self._etags: dict[str, str] = {}
        self._modified: dict[str, str] = {}

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
