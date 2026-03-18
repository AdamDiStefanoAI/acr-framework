"""Pillar 1: Identity & Purpose Binding — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class AgentRegisterRequest(BaseModel):
    agent_id: str
    owner: str
    purpose: str
    risk_tier: Literal["low", "medium", "high"] = "medium"
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    data_access: list[DataAccessEntry] = Field(default_factory=list)
    boundaries: AgentBoundaries = Field(default_factory=AgentBoundaries)


class AgentUpdateRequest(BaseModel):
    owner: str | None = None
    purpose: str | None = None
    risk_tier: Literal["low", "medium", "high"] | None = None
    allowed_tools: list[str] | None = None
    forbidden_tools: list[str] | None = None
    data_access: list[DataAccessEntry] | None = None
    boundaries: AgentBoundaries | None = None


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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    agent_id: str
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
