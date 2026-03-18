"""Pillar 1: Agent registry API endpoints."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.redis_client import get_redis_or_none
from acr.common.operator_auth import OperatorPrincipal, require_operator_roles
from acr.db.database import get_db
from acr.pillar1_identity import registry
from acr.pillar1_identity.models import (
    AgentRegisterRequest,
    AgentResponse,
    AgentUpdateRequest,
    TokenResponse,
)
from acr.pillar1_identity.validator import issue_token, validate_agent_identity

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/acr/agents", tags=["Identity"])

# Token issuance rate limit: 10 requests per agent_id per hour.
# Prevents an attacker with a valid agent_id from minting unlimited tokens.
_TOKEN_RATE_LIMIT = 10
_TOKEN_RATE_WINDOW_SECONDS = 3600  # 1 hour
_TOKEN_RATE_KEY_PREFIX = "acr:token:rate:"


async def _check_token_rate_limit(agent_id: str) -> None:
    """
    Increment the hourly token counter for this agent.
    Raises HTTP 429 if the limit is exceeded.
    Silently passes if Redis is unavailable (graceful degradation).
    """
    redis = get_redis_or_none()
    if redis is None:
        return  # degrade gracefully — never block issuance due to missing cache

    key = f"{_TOKEN_RATE_KEY_PREFIX}{agent_id}"
    try:
        count = await redis.incr(key)
        if count == 1:
            # First request in this window — set the TTL
            await redis.expire(key, _TOKEN_RATE_WINDOW_SECONDS)
        if count > _TOKEN_RATE_LIMIT:
            logger.warning("token_rate_limit_exceeded", agent_id=agent_id, count=count)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Token issuance rate limit exceeded "
                    f"({_TOKEN_RATE_LIMIT} per hour). Try again later."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis error — log and allow; never block issuance on cache failure
        logger.warning("token_rate_limit_redis_error", agent_id=agent_id, error=str(exc))


@router.post("", response_model=AgentResponse, status_code=201)
async def register_agent(
    req: AgentRegisterRequest,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin")),
) -> AgentResponse:
    """Register a new agent and return its manifest."""
    record = await registry.register_agent(db, req)
    return AgentResponse.model_validate(record)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "auditor", "security_admin")),
) -> list[AgentResponse]:
    records = await registry.list_agents(db)
    return [AgentResponse.model_validate(r) for r in records]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "auditor", "security_admin")),
) -> AgentResponse:
    record = await registry.get_agent(db, agent_id)
    return AgentResponse.model_validate(record)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    req: AgentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin")),
) -> AgentResponse:
    record = await registry.update_agent(db, agent_id, req)
    return AgentResponse.model_validate(record)


@router.delete("/{agent_id}", status_code=204)
async def deregister_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin")),
) -> None:
    await registry.deregister_agent(db, agent_id)


@router.post("/{agent_id}/token", response_model=TokenResponse)
async def issue_agent_token(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin")),
) -> TokenResponse:
    """Issue a short-lived JWT for an agent. Rate-limited to 10 requests per hour."""
    await _check_token_rate_limit(agent_id)
    # Verify agent exists and is active before issuing a token.
    await validate_agent_identity(db, agent_id, check_kill_switch=False)
    token, expires = issue_token(agent_id)
    return TokenResponse(agent_id=agent_id, access_token=token, expires_in_seconds=expires)
