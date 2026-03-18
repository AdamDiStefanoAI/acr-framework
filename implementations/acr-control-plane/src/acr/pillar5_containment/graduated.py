"""Pillar 5: Graduated response tiers — throttle → restrict → isolate → kill."""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.time import iso_utcnow
from acr.db.models import ContainmentActionRecord
from acr.pillar5_containment.killswitch import kill_agent
from acr.pillar5_containment.models import (
    ContainmentAction,
    ContainmentTier,
    DRIFT_THRESHOLDS,
)

logger = structlog.get_logger(__name__)


def tier_for_score(drift_score: float) -> ContainmentTier:
    """Return the containment tier appropriate for the given drift score."""
    if drift_score >= DRIFT_THRESHOLDS[ContainmentTier.KILL]:
        return ContainmentTier.KILL
    if drift_score >= DRIFT_THRESHOLDS[ContainmentTier.ISOLATE]:
        return ContainmentTier.ISOLATE
    if drift_score >= DRIFT_THRESHOLDS[ContainmentTier.RESTRICT]:
        return ContainmentTier.RESTRICT
    if drift_score >= DRIFT_THRESHOLDS[ContainmentTier.THROTTLE]:
        return ContainmentTier.THROTTLE
    return ContainmentTier.NONE


async def apply_graduated_response(
    db: AsyncSession,
    agent_id: str,
    drift_score: float,
    correlation_id: str | None = None,
) -> ContainmentAction | None:
    """
    Apply the appropriate containment tier based on drift score.
    Returns the action taken, or None if no action needed.
    """
    tier = tier_for_score(drift_score)
    if tier == ContainmentTier.NONE:
        return None

    action_type = {
        ContainmentTier.THROTTLE: "throttle",
        ContainmentTier.RESTRICT: "restrict",
        ContainmentTier.ISOLATE: "isolate",
        ContainmentTier.KILL: "kill",
    }[tier]

    reason = (
        f"Automated containment: drift_score={drift_score:.3f} triggered Tier {tier.value} ({action_type})"
    )

    logger.warning(
        "graduated_response",
        agent_id=agent_id,
        tier=tier.value,
        action_type=action_type,
        drift_score=drift_score,
        correlation_id=correlation_id,
    )

    # Persist to containment_actions table
    record = ContainmentActionRecord(
        agent_id=agent_id,
        action_type=action_type,
        tier=tier.value,
        reason=reason,
        drift_score=drift_score,
        correlation_id=correlation_id,
    )
    db.add(record)
    await db.flush()

    # Tier 4: actually invoke the kill switch
    if tier == ContainmentTier.KILL:
        await kill_agent(agent_id, reason=reason, operator_id="acr-drift-detector")

    return ContainmentAction(
        agent_id=agent_id,
        tier=tier,
        action_type=action_type,
        reason=reason,
        drift_score=drift_score,
        correlation_id=correlation_id,
    )
