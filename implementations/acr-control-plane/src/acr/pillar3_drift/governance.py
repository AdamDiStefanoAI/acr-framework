"""Governed baseline lifecycle for drift detection."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import BaselineNotFoundError
from acr.common.time import utcnow
from acr.db.models import DriftBaselineRecord, DriftBaselineVersionRecord
from acr.pillar3_drift.baseline import get_or_create_baseline, recompute_baseline


async def list_baseline_versions(db: AsyncSession, agent_id: str) -> list[DriftBaselineVersionRecord]:
    result = await db.execute(
        select(DriftBaselineVersionRecord)
        .where(DriftBaselineVersionRecord.agent_id == agent_id)
        .order_by(DriftBaselineVersionRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def get_baseline_version(
    db: AsyncSession,
    agent_id: str,
    baseline_version_id: str,
) -> DriftBaselineVersionRecord:
    result = await db.execute(
        select(DriftBaselineVersionRecord).where(
            DriftBaselineVersionRecord.agent_id == agent_id,
            DriftBaselineVersionRecord.baseline_version_id == baseline_version_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise BaselineNotFoundError(
            f"Baseline version '{baseline_version_id}' not found for agent '{agent_id}'"
        )
    return record


async def get_active_baseline_version(
    db: AsyncSession,
    agent_id: str,
) -> DriftBaselineVersionRecord | None:
    result = await db.execute(
        select(DriftBaselineVersionRecord).where(
            DriftBaselineVersionRecord.agent_id == agent_id,
            DriftBaselineVersionRecord.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def propose_baseline_version(
    db: AsyncSession,
    *,
    agent_id: str,
    actor: str,
    window_days: int = 30,
    notes: str | None = None,
) -> DriftBaselineVersionRecord:
    baseline = await recompute_baseline(db, agent_id, window_days=window_days)
    if baseline.sample_count <= 0 or not baseline.baseline_data:
        raise BaselineNotFoundError(
            f"Cannot propose baseline for agent '{agent_id}' without enough recorded drift samples"
        )

    record = DriftBaselineVersionRecord(
        baseline_version_id=f"blv-{uuid.uuid4()}",
        agent_id=agent_id,
        baseline_data=baseline.baseline_data,
        sample_count=baseline.sample_count,
        window_days=window_days,
        status="candidate",
        notes=notes,
        created_by=actor,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def approve_baseline_version(
    db: AsyncSession,
    *,
    agent_id: str,
    baseline_version_id: str,
    actor: str,
    notes: str | None = None,
) -> DriftBaselineVersionRecord:
    record = await get_baseline_version(db, agent_id, baseline_version_id)
    record.status = "approved"
    record.approved_by = actor
    record.approved_at = utcnow()
    if notes:
        record.notes = notes
    await db.flush()
    await db.refresh(record)
    return record


async def reject_baseline_version(
    db: AsyncSession,
    *,
    agent_id: str,
    baseline_version_id: str,
    actor: str,
    notes: str | None = None,
) -> DriftBaselineVersionRecord:
    record = await get_baseline_version(db, agent_id, baseline_version_id)
    record.status = "rejected"
    record.rejected_by = actor
    record.rejected_at = utcnow()
    if notes:
        record.notes = notes
    await db.flush()
    await db.refresh(record)
    return record


async def activate_baseline_version(
    db: AsyncSession,
    *,
    agent_id: str,
    baseline_version_id: str,
    actor: str,
    notes: str | None = None,
) -> DriftBaselineVersionRecord:
    record = await get_baseline_version(db, agent_id, baseline_version_id)
    if record.status not in {"approved", "active"}:
        raise BaselineNotFoundError(
            f"Baseline version '{baseline_version_id}' must be approved before activation"
        )

    result = await db.execute(
        select(DriftBaselineVersionRecord).where(
            DriftBaselineVersionRecord.agent_id == agent_id,
            DriftBaselineVersionRecord.status == "active",
            DriftBaselineVersionRecord.baseline_version_id != baseline_version_id,
        )
    )
    for active in result.scalars().all():
        active.status = "superseded"

    record.status = "active"
    record.activated_by = actor
    record.activated_at = utcnow()
    if notes:
        record.notes = notes

    current = await get_or_create_baseline(db, agent_id)
    current.baseline_data = record.baseline_data
    current.sample_count = record.sample_count
    current.last_updated_at = utcnow()

    await db.flush()
    await db.refresh(record)
    return record


async def sync_baseline_from_active_version(
    db: AsyncSession,
    agent_id: str,
) -> DriftBaselineRecord | None:
    active = await get_active_baseline_version(db, agent_id)
    if active is None:
        return None

    record = await get_or_create_baseline(db, agent_id)
    record.baseline_data = active.baseline_data
    record.sample_count = active.sample_count
    record.last_updated_at = utcnow()
    await db.flush()
    return record
