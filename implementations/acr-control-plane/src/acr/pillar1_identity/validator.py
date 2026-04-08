"""Pillar 1: Token validation and identity verification."""
from __future__ import annotations

from datetime import timedelta

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import (
    AgentKilledError,
    AgentLifecycleError,
    AgentNotFoundError,
    AgentNotRegisteredError,
    InvalidTokenError,
    TokenExpiredError,
)
from acr.common.time import utcnow
from acr.config import ALLOWED_JWT_ALGORITHMS, settings
from acr.db.models import AgentRecord
from acr.pillar1_identity.registry import ACTIVE_LIFECYCLE_STATES, get_agent


def issue_token(agent_id: str) -> tuple[str, int]:
    """Issue a short-lived JWT for the agent. Returns (token, expires_in_seconds)."""
    expire_seconds = settings.jwt_token_expire_minutes * 60
    expire_at = utcnow() + timedelta(seconds=expire_seconds)
    payload = {
        "sub": agent_id,
        "exp": expire_at,
        "iat": utcnow(),
        "iss": "acr-control-plane",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expire_seconds


def decode_token(token: str) -> str:
    """
    Decode and validate a JWT. Returns agent_id (sub claim).

    Explicitly pins the accepted algorithm list to ALLOWED_JWT_ALGORITHMS to
    prevent algorithm-confusion attacks (e.g., alg=none, alg=HS256 on RS256 key).
    """
    # Only accept the configured algorithm — never trust the token's header alone.
    if settings.jwt_algorithm not in ALLOWED_JWT_ALGORITHMS:
        raise InvalidTokenError(
            f"Configured JWT algorithm '{settings.jwt_algorithm}' is not allowed"
        )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],  # explicit allowlist, not token header
        )
        agent_id: str | None = payload.get("sub")
        if not agent_id:
            raise InvalidTokenError("Token missing subject claim")
        return agent_id
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredError("Token has expired") from exc
        raise InvalidTokenError(f"Invalid token: {exc}") from exc


async def validate_agent_identity(
    db: AsyncSession,
    agent_id: str,
    *,
    check_kill_switch: bool = True,
) -> AgentRecord:
    """
    Verify agent exists, is active, and (optionally) is not killed.

    The kill switch Redis check is done in the gateway before calling this;
    pass check_kill_switch=False to skip the DB-level active check only.
    """
    try:
        record = await get_agent(db, agent_id)
    except AgentNotFoundError:
        raise AgentNotRegisteredError(f"Agent '{agent_id}' is not registered")

    if not record.is_active:
        raise AgentNotRegisteredError(f"Agent '{agent_id}' is deregistered")

    # Lifecycle gate. `draft` agents have been registered but not yet
    # promoted to operational use, and `retired` agents are terminal.
    # Both must be blocked from the evaluate hot path.
    if record.lifecycle_state not in ACTIVE_LIFECYCLE_STATES:
        raise AgentLifecycleError(
            f"Agent '{agent_id}' is in lifecycle state '{record.lifecycle_state}' "
            f"and cannot evaluate actions"
        )

    return record
