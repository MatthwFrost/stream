# backend/src/api/main.py
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import articles, tags, sources, config
from src.api import websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(websocket.redis_listener())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="Stream News API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(articles.router)
    app.include_router(tags.router)
    app.include_router(sources.router)
    app.include_router(config.router)
    app.include_router(websocket.router)

    return app
