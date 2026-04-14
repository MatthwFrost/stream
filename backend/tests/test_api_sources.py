import pytest
from httpx import ASGITransport, AsyncClient
from src.api.main import create_app
from src.db import get_session

@pytest.fixture
def app(session):
    application = create_app()
    async def override_session():
        yield session
    application.dependency_overrides[get_session] = override_session
    return application

@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

async def test_create_source(client):
    resp = await client.post("/sources", json={
        "name": "Reuters", "type": "rss",
        "config": {"feed_url": "https://feeds.reuters.com/reuters/topNews"},
        "authority_score": 1.0, "poll_interval": 60,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Reuters"
    assert data["type"] == "rss"
    assert data["active"] is True

async def test_list_sources(client):
    await client.post("/sources", json={"name": "Reuters", "type": "rss",
        "config": {"feed_url": "https://example.com/feed"}, "authority_score": 1.0, "poll_interval": 60})
    await client.post("/sources", json={"name": "BBC", "type": "rss",
        "config": {"feed_url": "https://example.com/bbc"}, "authority_score": 0.9, "poll_interval": 60})
    resp = await client.get("/sources")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
