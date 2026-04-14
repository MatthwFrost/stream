import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models import Tag

router = APIRouter()


class TagCreate(BaseModel):
    name: str
    keywords: list[str]
    priority: int = 1


class TagUpdate(BaseModel):
    name: str | None = None
    keywords: list[str] | None = None
    priority: int | None = None
    active: bool | None = None


@router.get("/tags")
async def list_tags(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Tag).order_by(Tag.name))
    return [_serialize(t) for t in result.scalars()]


@router.post("/tags", status_code=201)
async def create_tag(body: TagCreate, session: AsyncSession = Depends(get_session)):
    tag = Tag(
        id=uuid.uuid4(),
        name=body.name,
        keywords=body.keywords,
        priority=body.priority,
        active=True,
    )
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return _serialize(tag)


@router.put("/tags/{tag_id}")
async def update_tag(tag_id: str, body: TagUpdate, session: AsyncSession = Depends(get_session)):
    tag = await session.get(Tag, uuid.UUID(tag_id))
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if body.name is not None:
        tag.name = body.name
    if body.keywords is not None:
        tag.keywords = body.keywords
    if body.priority is not None:
        tag.priority = body.priority
    if body.active is not None:
        tag.active = body.active
    await session.commit()
    await session.refresh(tag)
    return _serialize(tag)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: str, session: AsyncSession = Depends(get_session)):
    tag = await session.get(Tag, uuid.UUID(tag_id))
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    await session.delete(tag)
    await session.commit()


def _serialize(tag: Tag) -> dict:
    return {
        "id": str(tag.id),
        "name": tag.name,
        "keywords": tag.keywords,
        "priority": tag.priority,
        "active": tag.active,
    }
