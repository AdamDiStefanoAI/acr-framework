"""Pillar 1: Identity & Purpose Binding — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Lifecycle: agents move draft → active → deprecated → retired.
#  - draft:      registered but not yet allowed to evaluate (initial setup)
#  - active:     fully operational
#  - deprecated: still works but a warning is emitted; new dependents discouraged
#  - retired:    blocked from evaluating; equivalent to legacy is_active=False
LifecycleState = Literal["draft", "active", "deprecated", "retired"]

# Health is observed via heartbeats — `unknown` is the default until the first
# heartbeat arrives. The sweep loop downgrades stale agents to `unhealthy`.
HealthStatus = Literal["unknown", "healthy", "degraded", "unhealthy"]


class DataAccessEntry(BaseModel):
    resource: str
    permission: Literal["READ", "READ_WRITE", "WRITE", "NONE"] = "READ"


class AgentBoundaries(BaseModel):
    max_actions_per_minute: int = 30
    max_cost_per_hour_usd: float = 5.0
    allowed_regions: list[str] = Field(default_factory=list)
    credential_rotation_days: int = 90


class AgentManifest(BaseModel):
    """ACR agent manifest — matches the spec YAML schema."""

    agent_id: str = Field(..., description="Unique agent identifier")
    owner: str = Field(..., description="Owning team email or name")
    purpose: str = Field(..., description="Declared business purpose of the agent")
    risk_tier: Literal["low", "medium", "high"] = "medium"
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    data_access: list[DataAccessEntry] = Field(default_factory=list)
    boundaries: AgentBoundaries = Field(default_factory=AgentBoundaries)
    # Registry expansion fields. Defaulted so existing manifest consumers
    # (e.g. drift governance event emission) keep working without changes.
    version: str = "1.0.0"
    parent_agent_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class AgentRegisterRequest(BaseModel):
    agent_id: str
    owner: str
    purpose: str
    risk_tier: Literal["low", "medium", "high"] = "medium"
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    data_access: list[DataAccessEntry] = Field(default_factory=list)
    boundaries: AgentBoundaries = Field(default_factory=AgentBoundaries)
    # Optional on registration — sensible defaults preserve current behaviour.
    version: str = "1.0.0"
    parent_agent_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    # Operators can register an agent in `draft` and promote it later, or
    # register directly as `active` (the historical default).
    lifecycle_state: LifecycleState = "active"


class AgentUpdateRequest(BaseModel):
    owner: str | None = None
    purpose: str | None = None
    risk_tier: Literal["low", "medium", "high"] | None = None
    allowed_tools: list[str] | None = None
    forbidden_tools: list[str] | None = None
    data_access: list[DataAccessEntry] | None = None
    boundaries: AgentBoundaries | None = None
    version: str | None = None
    capabilities: list[str] | None = None
    # NOTE: parent_agent_id and lifecycle_state are intentionally NOT mutable
    # via this generic update endpoint — they have dedicated transition
    # endpoints with their own validation.


class LifecycleTransitionRequest(BaseModel):
    """Request to move an agent into a new lifecycle state."""

    target_state: LifecycleState
    reason: str | None = Field(
        default=None,
        description="Operator-supplied justification (recorded in audit telemetry)",
    )


class HeartbeatRequest(BaseModel):
    """Optional payload for agent self-reported health."""

    health_status: HealthStatus = "healthy"
    notes: str | None = None


class AgentResponse(BaseModel):
    agent_id: str
    owner: str
    purpose: str
    risk_tier: str
    allowed_tools: list[str]
    forbidden_tools: list[str]
    data_access: list[DataAccessEntry]
    boundaries: AgentBoundaries
    is_active: bool
    version: str
    parent_agent_id: str | None
    capabilities: list[str]
    lifecycle_state: LifecycleState
    health_status: HealthStatus
    last_heartbeat_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentLineageNode(BaseModel):
    """One node in an agent lineage chain."""

    agent_id: str
    version: str
    lifecycle_state: LifecycleState
    parent_agent_id: str | None


class AgentLineageResponse(BaseModel):
    agent_id: str
    # Ordered root → leaf. The first element is the topmost ancestor; the
    # last element is the queried agent itself.
    ancestors: list[AgentLineageNode]
    # Direct children only (one level). Callers can recurse if needed.
    children: list[AgentLineageNode]


class TokenResponse(BaseModel):
    agent_id: str
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
