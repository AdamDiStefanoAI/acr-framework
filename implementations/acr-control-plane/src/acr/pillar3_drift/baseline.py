"""Pillar 3: Baseline collection and storage."""
from __future__ import annotations

import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.time import iso_utcnow, utcnow
from acr.db.models import DriftBaselineRecord, DriftMetricRecord
from acr.pillar3_drift.models import BaselineProfile
from acr.pillar3_drift.signals import MIN_BASELINE_SAMPLES


async def record_metric_sample(
    db: AsyncSession,
    *,
    agent_id: str,
    correlation_id: str,
    tool_name: str | None,
    action_type: str | None,
    policy_denied: bool,
    latency_ms: int | None,
) -> None:
    """Store a single raw metric sample."""
    sample = DriftMetricRecord(
        agent_id=agent_id,
        correlation_id=correlation_id,
        tool_name=tool_name,
        action_type=action_type,
        policy_denied=policy_denied,
        latency_ms=latency_ms,
    )
    db.add(sample)
    await db.flush()


async def get_or_create_baseline(db: AsyncSession, agent_id: str) -> DriftBaselineRecord:
    result = await db.execute(
        select(DriftBaselineRecord).where(DriftBaselineRecord.agent_id == agent_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        record = DriftBaselineRecord(
            agent_id=agent_id,
            baseline_data={},
            sample_count=0,
            collection_started_at=utcnow(),
        )
        db.add(record)
        await db.flush()
    return record


async def recompute_baseline(db: AsyncSession, agent_id: str, window_days: int = 30) -> DriftBaselineRecord:
    """
    Recompute baseline statistics from recent metric samples.
    Uses mean + std for each behavioral signal.
    """
    cutoff = utcnow() - timedelta(days=window_days)
    result = await db.execute(
        select(DriftMetricRecord)
        .where(
            DriftMetricRecord.agent_id == agent_id,
            DriftMetricRecord.created_at >= cutoff,
        )
        .order_by(DriftMetricRecord.created_at.asc())
    )
    samples = result.scalars().all()

    if not samples:
        return await get_or_create_baseline(db, agent_id)

    n = len(samples)

    # tool call frequency (calls per minute, estimated from window)
    window_minutes = max(1, window_days * 24 * 60)
    freq = n / window_minutes

    # denial rate
    denials = sum(1 for s in samples if s.policy_denied)
    denial_rate = denials / n

    # error rate (use latency=None as proxy for errors; proper signal is tool error flag)
    errors = sum(1 for s in samples if s.latency_ms is None)
    error_rate = errors / n

    # action diversity — Shannon entropy of tool distribution
    tool_counts: dict[str, int] = {}
    for s in samples:
        t = s.tool_name or "_unknown"
        tool_counts[t] = tool_counts.get(t, 0) + 1
    entropy = 0.0
    for count in tool_counts.values():
        p = count / n
        entropy -= p * math.log2(p)
    max_entropy = math.log2(len(tool_counts)) if len(tool_counts) > 1 else 1.0
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    # Build baseline data — store mean + std (we estimate std from sliding window for now)
    # For a real system you'd accumulate Welford's online algorithm values.
    baseline_data = {
        "tool_call_frequency": {"mean": freq, "std": max(0.01, freq * 0.3), "count": n},
        "denial_rate": {"mean": denial_rate, "std": max(0.01, denial_rate * 0.5 + 0.02), "count": n},
        "error_rate": {"mean": error_rate, "std": max(0.01, error_rate * 0.5 + 0.01), "count": n},
        "action_diversity": {"mean": normalized_entropy, "std": max(0.05, normalized_entropy * 0.2), "count": n},
    }

    record = await get_or_create_baseline(db, agent_id)
    record.baseline_data = baseline_data
    record.sample_count = n
    record.last_updated_at = utcnow()
    await db.flush()
    return record


async def reset_baseline(db: AsyncSession, agent_id: str) -> DriftBaselineRecord:
    """Reset baseline — clears stored data so recollection begins fresh."""
    record = await get_or_create_baseline(db, agent_id)
    record.baseline_data = {}
    record.sample_count = 0
    record.collection_started_at = utcnow()
    record.last_updated_at = utcnow()
    await db.flush()
    return record


async def get_baseline_profile(db: AsyncSession, agent_id: str) -> BaselineProfile:
    record = await get_or_create_baseline(db, agent_id)
    return BaselineProfile(
        agent_id=agent_id,
        metrics=record.baseline_data or {},
        sample_count=record.sample_count,
        collection_started_at=record.collection_started_at.isoformat() if record.collection_started_at else None,
        last_updated_at=record.last_updated_at.isoformat() if record.last_updated_at else None,
    )
