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
        for tag_data in INITIAL_TAGS:
            exists = await session.execute(
                select(Tag).where(Tag.name == tag_data["name"])
            )
            if exists.scalar_one_or_none() is None:
                session.add(Tag(id=uuid.uuid4(), active=True, **tag_data))
                print(f"  + Tag: {tag_data['name']}")

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
