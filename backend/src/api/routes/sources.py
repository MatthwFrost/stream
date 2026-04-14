import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_session
from src.models import Source

router = APIRouter()


class SourceCreate(BaseModel):
    name: str
    type: str
    config: dict
    authority_score: float = 0.5
    poll_interval: int = 60


@router.get("/sources")
async def list_sources(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Source).order_by(Source.name))
    return [_serialize(s) for s in result.scalars()]


@router.post("/sources", status_code=201)
async def create_source(body: SourceCreate, session: AsyncSession = Depends(get_session)):
    source = Source(id=uuid.uuid4(), name=body.name, type=body.type, config=body.config,
                    authority_score=body.authority_score, poll_interval=body.poll_interval, active=True)
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return _serialize(source)


def _serialize(source: Source) -> dict:
    return {"id": str(source.id), "name": source.name, "type": source.type,
            "config": source.config, "authority_score": source.authority_score,
            "poll_interval": source.poll_interval, "active": source.active}
