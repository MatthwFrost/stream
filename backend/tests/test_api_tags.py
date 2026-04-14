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


async def test_create_tag(client):
    resp = await client.post("/tags", json={
        "name": "technology",
        "keywords": ["tech", "AI", "software"],
        "priority": 1,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "technology"
    assert data["keywords"] == ["tech", "AI", "software"]
    assert data["active"] is True


async def test_list_tags(client):
    await client.post("/tags", json={"name": "tech", "keywords": ["tech"], "priority": 1})
    await client.post("/tags", json={"name": "oil", "keywords": ["oil"], "priority": 2})
    resp = await client.get("/tags")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_tag(client):
    create_resp = await client.post("/tags", json={"name": "tech", "keywords": ["tech"], "priority": 1})
    tag_id = create_resp.json()["id"]
    resp = await client.put(f"/tags/{tag_id}", json={
        "keywords": ["tech", "AI", "ML"],
        "priority": 3,
    })
    assert resp.status_code == 200
    assert resp.json()["keywords"] == ["tech", "AI", "ML"]
    assert resp.json()["priority"] == 3


async def test_delete_tag(client):
    create_resp = await client.post("/tags", json={"name": "temp", "keywords": ["temp"], "priority": 1})
    tag_id = create_resp.json()["id"]
    resp = await client.delete(f"/tags/{tag_id}")
    assert resp.status_code == 204
    list_resp = await client.get("/tags")
    assert len(list_resp.json()) == 0
