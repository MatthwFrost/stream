# backend/src/api/websocket.py
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.redis_pubsub import subscribe_articles

logger = logging.getLogger(__name__)
router = APIRouter()

connected_clients: set[WebSocket] = set()


async def broadcast(message: dict):
    dead = set()
    for ws in connected_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)


async def redis_listener():
    try:
        async for article_data in subscribe_articles():
            await broadcast({"type": "new_article", "data": article_data})
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Redis listener error: {e}")


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)
    logger.info(f"Client connected. Total: {len(connected_clients)}")
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(ws)
        logger.info(f"Client disconnected. Total: {len(connected_clients)}")
