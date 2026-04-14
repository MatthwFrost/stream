# backend/tests/test_websocket.py
from unittest.mock import patch, AsyncMock

from starlette.testclient import TestClient

from src.api.main import create_app


def test_websocket_connects():
    with patch("src.api.websocket.redis_listener", new_callable=AsyncMock):
        app = create_app()
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"
