from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models import Config

router = APIRouter()

# The API keys we expose to the UI — key name → display label
KNOWN_KEYS = {
    "newsapi_key": "NewsAPI",
    "gnews_api_key": "GNews",
}


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


class ConfigEntry(BaseModel):
    key: str
    label: str
    masked_value: str | None  # None means not set


class ConfigSet(BaseModel):
    value: str


@router.get("/config")
async def get_config(session: AsyncSession = Depends(get_session)) -> list[ConfigEntry]:
    result = await session.execute(select(Config).where(Config.key.in_(KNOWN_KEYS.keys())))
    stored = {row.key: row.value for row in result.scalars()}

    return [
        ConfigEntry(
            key=key,
            label=label,
            masked_value=_mask(stored[key]) if key in stored else None,
        )
        for key, label in KNOWN_KEYS.items()
    ]


@router.put("/config/{key}", status_code=204)
async def set_config(key: str, body: ConfigSet, session: AsyncSession = Depends(get_session)):
    if key not in KNOWN_KEYS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown config key")

    existing = await session.get(Config, key)
    if existing:
        existing.value = body.value.strip()
    else:
        session.add(Config(key=key, value=body.value.strip()))
    await session.commit()


@router.delete("/config/{key}", status_code=204)
async def delete_config(key: str, session: AsyncSession = Depends(get_session)):
    if key not in KNOWN_KEYS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown config key")

    existing = await session.get(Config, key)
    if existing:
        await session.delete(existing)
        await session.commit()
