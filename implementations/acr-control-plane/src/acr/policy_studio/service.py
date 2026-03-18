from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import PolicyDraftNotFoundError
from acr.db.models import PolicyDraftRecord
from acr.policy_studio.models import PolicyDraftUpsertRequest


async def list_policy_drafts(db: AsyncSession) -> list[PolicyDraftRecord]:
    result = await db.execute(
        select(PolicyDraftRecord).order_by(PolicyDraftRecord.updated_at.desc(), PolicyDraftRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def get_policy_draft(db: AsyncSession, draft_id: str) -> PolicyDraftRecord:
    result = await db.execute(
        select(PolicyDraftRecord).where(PolicyDraftRecord.draft_id == draft_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise PolicyDraftNotFoundError(f"Policy draft '{draft_id}' not found")
    return record


async def create_policy_draft(
    db: AsyncSession,
    *,
    req: PolicyDraftUpsertRequest,
    actor: str,
) -> PolicyDraftRecord:
    record = PolicyDraftRecord(
        draft_id=f"pdr-{uuid.uuid4()}",
        name=req.name,
        agent_id=req.agent_id,
        template=req.template,
        manifest=req.manifest,
        rego_policy=req.rego_policy,
        wizard_inputs=req.wizard_inputs,
        created_by=actor,
        updated_by=actor,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def update_policy_draft(
    db: AsyncSession,
    *,
    draft_id: str,
    req: PolicyDraftUpsertRequest,
    actor: str,
) -> PolicyDraftRecord:
    record = await get_policy_draft(db, draft_id)
    record.name = req.name
    record.agent_id = req.agent_id
    record.template = req.template
    record.manifest = req.manifest
    record.rego_policy = req.rego_policy
    record.wizard_inputs = req.wizard_inputs
    record.updated_by = actor
    await db.flush()
    await db.refresh(record)
    return record
