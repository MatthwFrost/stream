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
