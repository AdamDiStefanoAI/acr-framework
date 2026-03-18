"""Pillar 1: Agent registry — CRUD backed by PostgreSQL."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import AgentAlreadyExistsError, AgentNotFoundError
from acr.common.time import utcnow
from acr.db.models import AgentRecord
from acr.pillar1_identity.models import (
    AgentBoundaries,
    AgentManifest,
    AgentRegisterRequest,
    AgentUpdateRequest,
)


def _record_to_manifest(record: AgentRecord) -> AgentManifest:
    return AgentManifest(
        agent_id=record.agent_id,
        owner=record.owner,
        purpose=record.purpose,
        risk_tier=record.risk_tier,
        allowed_tools=record.allowed_tools or [],
        forbidden_tools=record.forbidden_tools or [],
        data_access=record.data_access or [],
        boundaries=AgentBoundaries(**(record.boundaries or {})),
    )


async def register_agent(db: AsyncSession, req: AgentRegisterRequest) -> AgentRecord:
    """Insert a new agent record. Returns the ORM record."""
    record = AgentRecord(
        agent_id=req.agent_id,
        owner=req.owner,
        purpose=req.purpose,
        risk_tier=req.risk_tier,
        allowed_tools=req.allowed_tools,
        forbidden_tools=req.forbidden_tools,
        data_access=[e.model_dump() for e in req.data_access],
        boundaries=req.boundaries.model_dump(),
        is_active=True,
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise AgentAlreadyExistsError(
            f"Agent '{req.agent_id}' is already registered"
        ) from exc
    await db.refresh(record)
    return record


async def get_agent(db: AsyncSession, agent_id: str) -> AgentRecord:
    result = await db.execute(select(AgentRecord).where(AgentRecord.agent_id == agent_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise AgentNotFoundError(f"Agent '{agent_id}' not found")
    return record


async def list_agents(db: AsyncSession) -> list[AgentRecord]:
    result = await db.execute(select(AgentRecord).order_by(AgentRecord.created_at.desc()))
    return list(result.scalars().all())


async def update_agent(db: AsyncSession, agent_id: str, req: AgentUpdateRequest) -> AgentRecord:
    record = await get_agent(db, agent_id)
    if req.owner is not None:
        record.owner = req.owner
    if req.purpose is not None:
        record.purpose = req.purpose
    if req.risk_tier is not None:
        record.risk_tier = req.risk_tier
    if req.allowed_tools is not None:
        record.allowed_tools = req.allowed_tools
    if req.forbidden_tools is not None:
        record.forbidden_tools = req.forbidden_tools
    if req.data_access is not None:
        record.data_access = [e.model_dump() for e in req.data_access]
    if req.boundaries is not None:
        record.boundaries = req.boundaries.model_dump()
    record.updated_at = utcnow()
    await db.flush()
    await db.refresh(record)
    return record


async def deregister_agent(db: AsyncSession, agent_id: str) -> None:
    record = await get_agent(db, agent_id)
    record.is_active = False
    await db.flush()


async def get_manifest(db: AsyncSession, agent_id: str) -> AgentManifest:
    record = await get_agent(db, agent_id)
    return _record_to_manifest(record)
