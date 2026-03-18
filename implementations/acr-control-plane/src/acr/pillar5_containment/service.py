"""
Pillar 5: Independent Kill Switch Service.

This runs as a SEPARATE FastAPI service in its own container (port 8443).
It must NOT run inside the gateway process.

State is stored in Redis for sub-millisecond reads.
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import timezone
from datetime import datetime
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

_redis: aioredis.Redis | None = None

KILL_KEY_PREFIX = "acr:kill:"
KILLSWITCH_SECRET = os.getenv("KILLSWITCH_SECRET", "killswitch_dev_secret_change_me")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OPERATOR_API_KEYS_JSON = os.getenv("OPERATOR_API_KEYS_JSON", "")


def _operator_identities() -> dict[str, dict]:
    if not OPERATOR_API_KEYS_JSON:
        return {}
    raw = json.loads(OPERATOR_API_KEYS_JSON)
    if not isinstance(raw, dict):
        raise RuntimeError("OPERATOR_API_KEYS_JSON must decode to an object")
    return raw


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis
    _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield
    if _redis:
        await _redis.aclose()


app = FastAPI(title="ACR Kill Switch Service", version="1.0.0", lifespan=lifespan)


def _redis_client() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis


def _require_secret(x_killswitch_secret: str | None) -> None:
    if x_killswitch_secret != KILLSWITCH_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid kill switch secret")


def _require_operator(
    x_operator_api_key: str | None,
    *required_roles: str,
) -> str:
    if not x_operator_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Operator-API-Key header is required",
        )
    for expected_key, identity in _operator_identities().items():
        if secrets.compare_digest(x_operator_api_key, expected_key):
            subject = str(identity.get("subject") or "operator")
            roles = set(identity.get("roles") or [])
            if required_roles and roles.isdisjoint(required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Operator lacks required role",
                )
            return subject
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid operator API key")


# ── Models ────────────────────────────────────────────────────────────────────

class KillRequest(BaseModel):
    agent_id: str
    reason: str
    operator_id: str | None = None


class RestoreRequest(BaseModel):
    agent_id: str
    reason: str | None = None
    operator_id: str | None = None


class KillState(BaseModel):
    agent_id: str
    is_killed: bool
    reason: str | None = None
    killed_at: str | None = None
    killed_by: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    try:
        await _redis_client().ping()
        return {"status": "healthy", "redis": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unhealthy: {exc}")


@app.get("/ready")
async def ready() -> dict:
    return await health()


@app.post("/acr/kill", response_model=KillState)
async def kill_agent(
    req: KillRequest,
    x_killswitch_secret: str | None = Header(default=None),
    x_operator_api_key: str | None = Header(default=None),
) -> KillState:
    """Activate kill switch for an agent. Writes state to Redis."""
    _require_secret(x_killswitch_secret)
    operator_subject = _require_operator(x_operator_api_key, "security_admin", "killswitch_operator")
    r = _redis_client()
    key = f"{KILL_KEY_PREFIX}{req.agent_id}"
    killed_at = datetime.now(timezone.utc).isoformat()
    await r.hset(key, mapping={  # type: ignore[misc]
        "is_killed": "1",
        "reason": req.reason,
        "killed_at": killed_at,
        "killed_by": req.operator_id or operator_subject,
    })
    return KillState(
        agent_id=req.agent_id,
        is_killed=True,
        reason=req.reason,
        killed_at=killed_at,
        killed_by=req.operator_id or operator_subject,
    )


@app.post("/acr/kill/restore", response_model=KillState)
async def restore_agent(
    req: RestoreRequest,
    x_killswitch_secret: str | None = Header(default=None),
    x_operator_api_key: str | None = Header(default=None),
) -> KillState:
    """Restore an agent from killed state."""
    _require_secret(x_killswitch_secret)
    _require_operator(x_operator_api_key, "security_admin", "killswitch_operator")
    r = _redis_client()
    key = f"{KILL_KEY_PREFIX}{req.agent_id}"
    await r.delete(key)
    return KillState(agent_id=req.agent_id, is_killed=False)


@app.get("/acr/kill/status/{agent_id}", response_model=KillState)
async def get_status(
    agent_id: str,
    x_killswitch_secret: str | None = Header(default=None),
    x_operator_api_key: str | None = Header(default=None),
) -> KillState:
    """Query kill state for a single agent. Requires X-Killswitch-Secret header."""
    _require_secret(x_killswitch_secret)
    _require_operator(x_operator_api_key, "security_admin", "killswitch_operator", "auditor")
    r = _redis_client()
    key = f"{KILL_KEY_PREFIX}{agent_id}"
    data = await r.hgetall(key)
    if not data:
        return KillState(agent_id=agent_id, is_killed=False)
    return KillState(
        agent_id=agent_id,
        is_killed=data.get("is_killed") == "1",
        reason=data.get("reason"),
        killed_at=data.get("killed_at"),
        killed_by=data.get("killed_by"),
    )


@app.get("/acr/kill/status", response_model=list[KillState])
async def list_status(
    x_killswitch_secret: str | None = Header(default=None),
    x_operator_api_key: str | None = Header(default=None),
) -> list[KillState]:
    """List all currently killed agents. Requires X-Killswitch-Secret header."""
    _require_secret(x_killswitch_secret)
    _require_operator(x_operator_api_key, "security_admin", "killswitch_operator", "auditor")
    r = _redis_client()
    keys = await r.keys(f"{KILL_KEY_PREFIX}*")
    result: list[KillState] = []
    for key in keys:
        data = await r.hgetall(key)
        agent_id = key.removeprefix(KILL_KEY_PREFIX)
        result.append(KillState(
            agent_id=agent_id,
            is_killed=data.get("is_killed") == "1",
            reason=data.get("reason"),
            killed_at=data.get("killed_at"),
            killed_by=data.get("killed_by"),
        ))
    return result
