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
    async with async_session() as session:
        raw_articles = await newsapi_agent.fetch_top_headlines(session)
        count = 0
        for raw in raw_articles:
            result = await ingest_article(raw, session)
            if result:
                count += 1
    if count > 0:
        logger.info(f"NewsAPI: ingested {count} new articles")


async def run_scraper_sources():
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
    async with async_session() as session:
        await run_ranker(session)


async def periodic(coro_fn, interval_seconds: int, name: str):
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
