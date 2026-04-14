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
