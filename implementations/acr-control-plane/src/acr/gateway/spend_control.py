"""Shared authoritative spend-control helpers for gateway and approval execution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from acr.common.errors import AuthoritativeSpendControlError, RuntimeControlDependencyError
from acr.common.redis_client import get_redis_or_none
from acr.config import runtime_dependencies_fail_closed, settings

_SPEND_KEY_PREFIX = "acr:spend:"


def _hour_bucket() -> str:
    now = datetime.now(UTC)
    return now.strftime("%Y%m%d%H")


def _extract_boundaries(manifest: Any) -> dict[str, Any]:
    if hasattr(manifest, "boundaries"):
        boundaries = manifest.boundaries
        if hasattr(boundaries, "model_dump"):
            return boundaries.model_dump()
        if isinstance(boundaries, dict):
            return boundaries
    if isinstance(manifest, dict):
        boundaries = manifest.get("boundaries")
        if isinstance(boundaries, dict):
            return boundaries
    return {}


def resolve_action_cost_usd(manifest: Any, tool_name: str) -> float:
    boundaries = _extract_boundaries(manifest)
    tool_costs = boundaries.get("tool_costs_usd") or {}
    if tool_name in tool_costs:
        return float(tool_costs[tool_name])

    default_cost = boundaries.get("default_action_cost_usd")
    if default_cost is not None:
        return float(default_cost)

    if settings.acr_env in ("development", "test"):
        return 0.0

    raise AuthoritativeSpendControlError(
        f"No authoritative spend estimate configured for tool '{tool_name}'"
    )


async def get_authoritative_projected_spend(
    agent_id: str,
    estimated_action_cost_usd: float,
) -> float:
    redis = get_redis_or_none()
    if redis is None:
        if runtime_dependencies_fail_closed():
            raise RuntimeControlDependencyError(
                "Authoritative spend ledger unavailable: Redis is not initialized"
            )
        return round(float(estimated_action_cost_usd), 4)

    key = f"{_SPEND_KEY_PREFIX}{agent_id}:{_hour_bucket()}"
    try:
        current = await redis.get(key)
        current_spend = float(current) if current else 0.0
        return round(current_spend + float(estimated_action_cost_usd), 4)
    except Exception as exc:
        if runtime_dependencies_fail_closed():
            raise RuntimeControlDependencyError(
                f"Authoritative spend ledger unavailable: {exc}"
            ) from exc
        return round(float(estimated_action_cost_usd), 4)


async def adjust_authoritative_spend(agent_id: str, delta_usd: float) -> None:
    if delta_usd == 0:
        return

    redis = get_redis_or_none()
    if redis is None:
        if runtime_dependencies_fail_closed():
            raise RuntimeControlDependencyError(
                "Authoritative spend ledger unavailable during commit: Redis is not initialized"
            )
        return

    key = f"{_SPEND_KEY_PREFIX}{agent_id}:{_hour_bucket()}"
    try:
        await redis.incrbyfloat(key, float(delta_usd))
        await redis.expire(key, 7200)
    except Exception as exc:
        if runtime_dependencies_fail_closed():
            raise RuntimeControlDependencyError(
                f"Authoritative spend ledger unavailable during commit: {exc}"
            ) from exc
