# backend/src/services/config_store.py
"""Helpers to fetch runtime config values from the DB, with env-var fallback."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Config
from src.config import settings


async def get_api_key(key: str, session: AsyncSession) -> str:
    """Return the API key from DB if set, else fall back to the env-var setting."""
    result = await session.get(Config, key)
    if result and result.value:
        return result.value
    # env-var fallback
    return getattr(settings, key, "")
