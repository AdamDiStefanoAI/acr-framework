"""Pillar 6: Action risk tiering — classify actions for approval routing."""
from __future__ import annotations

from typing import NamedTuple

from acr.pillar6_authority.models import RiskTier


class TierResult(NamedTuple):
    tier: RiskTier
    approval_queue: str
    sla_minutes: int
    auto_approve: bool


# OPA drives tiering in production; this provides a sensible fallback.
# The gateway uses the OPA escalate decision + queue from policy evaluation.
def classify_action(
    tool_name: str,
    parameters: dict,
    agent_risk_tier: str,
) -> TierResult:
    """
    Classify an action into low/medium/high risk.
    In production this is done by OPA returning `escalate=true` with metadata.
    This function is used as a fallback when OPA doesn't provide tier info.
    """
    # High-risk: destructive or high-value operations
    HIGH_RISK_TOOLS = {
        "delete_customer",
        "delete_record",
        "issue_refund",
        "modify_billing",
        "send_bulk_email",
        "drop_table",
        "execute_sql",
    }
    # Medium-risk: writes and mutations
    MEDIUM_RISK_TOOLS = {
        "create_ticket",
        "update_customer",
        "send_email",
        "create_record",
    }

    if tool_name in HIGH_RISK_TOOLS:
        return TierResult(tier="high", approval_queue="high-risk-approvals", sla_minutes=240, auto_approve=False)

    if tool_name in MEDIUM_RISK_TOOLS:
        if agent_risk_tier == "high":
            return TierResult(tier="medium", approval_queue="medium-risk-approvals", sla_minutes=60, auto_approve=False)
        return TierResult(tier="low", approval_queue="default", sla_minutes=0, auto_approve=True)

    # Default: low risk
    return TierResult(tier="low", approval_queue="default", sla_minutes=0, auto_approve=True)
