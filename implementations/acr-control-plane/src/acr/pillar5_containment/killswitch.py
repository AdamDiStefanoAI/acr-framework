"""Pillar 5: Kill switch client.

Hot-path reads (is_agent_killed) go directly to Redis — sub-millisecond latency,
no dependency on the kill switch service being up for reads.

Write operations (kill/restore) call the independent kill switch service so that
the service is the single authoritative writer.
"""
from __future__ import annotations

import structlog
import httpx

from acr.common.errors import KillSwitchError
from acr.common.redis_client import get_redis_or_none
from acr.config import settings
from acr.pillar5_containment.models import KillSwitchState

logger = structlog.get_logger(__name__)

# Shared key prefix — must match the kill switch service
KILL_KEY_PREFIX = "acr:kill:"


async def is_agent_killed(agent_id: str) -> bool:
    """
    Check kill switch state by reading Redis directly.
    Fails secure if Redis is unavailable or the read errors.
    This is the hot path: called on every /acr/evaluate request.
    """
    redis = get_redis_or_none()
    if redis is None:
        logger.error("killswitch_redis_unavailable", agent_id=agent_id)
        raise KillSwitchError("Kill switch state unavailable: Redis is not initialized")
    try:
        val = await redis.hget(f"{KILL_KEY_PREFIX}{agent_id}", "is_killed")
        return val == "1"
    except Exception as exc:
        logger.error("killswitch_redis_read_failed", agent_id=agent_id, error=str(exc))
        raise KillSwitchError("Kill switch state unavailable: Redis read failed") from exc


async def kill_agent(agent_id: str, reason: str, operator_id: str | None = None) -> KillSwitchState:
    """Activate the kill switch for an agent via the independent service."""
    try:
        async with httpx.AsyncClient(base_url=settings.killswitch_url, timeout=5.0) as client:
            resp = await client.post(
                "/acr/kill",
                json={"agent_id": agent_id, "reason": reason, "operator_id": operator_id},
                headers={
                    "X-Killswitch-Secret": settings.killswitch_secret,
                    "X-Operator-API-Key": settings.service_operator_api_key,
                },
            )
            resp.raise_for_status()
            return KillSwitchState(**resp.json())
    except httpx.HTTPStatusError as exc:
        raise KillSwitchError(f"Kill switch returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise KillSwitchError(f"Kill switch unreachable: {exc}") from exc


async def restore_agent(agent_id: str, operator_id: str | None = None) -> KillSwitchState:
    """Restore an agent from killed state."""
    try:
        async with httpx.AsyncClient(base_url=settings.killswitch_url, timeout=5.0) as client:
            resp = await client.post(
                "/acr/kill/restore",
                json={"agent_id": agent_id, "operator_id": operator_id},
                headers={
                    "X-Killswitch-Secret": settings.killswitch_secret,
                    "X-Operator-API-Key": settings.service_operator_api_key,
                },
            )
            resp.raise_for_status()
            return KillSwitchState(**resp.json())
    except httpx.HTTPStatusError as exc:
        raise KillSwitchError(f"Kill switch returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise KillSwitchError(f"Kill switch unreachable: {exc}") from exc


async def get_kill_status(agent_id: str) -> KillSwitchState:
    """Query kill switch state for an agent via the independent service."""
    try:
        async with httpx.AsyncClient(base_url=settings.killswitch_url, timeout=5.0) as client:
            resp = await client.get(
                f"/acr/kill/status/{agent_id}",
                headers={
                    "X-Killswitch-Secret": settings.killswitch_secret,
                    "X-Operator-API-Key": settings.service_operator_api_key,
                },
            )
            resp.raise_for_status()
            return KillSwitchState(**resp.json())
    except httpx.HTTPStatusError as exc:
        raise KillSwitchError(f"Kill switch returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise KillSwitchError(f"Kill switch unreachable: {exc}") from exc


async def list_kill_status() -> list[KillSwitchState]:
    """List all kill switch states via the independent service."""
    try:
        async with httpx.AsyncClient(base_url=settings.killswitch_url, timeout=5.0) as client:
            resp = await client.get(
                "/acr/kill/status",
                headers={
                    "X-Killswitch-Secret": settings.killswitch_secret,
                    "X-Operator-API-Key": settings.service_operator_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [KillSwitchState(**item) for item in data]
    except httpx.HTTPStatusError as exc:
        raise KillSwitchError(f"Kill switch returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise KillSwitchError(f"Kill switch unreachable: {exc}") from exc
