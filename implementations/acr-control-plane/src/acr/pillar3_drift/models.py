"""Pillar 3: Autonomy Drift Detection — models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DriftSignal(BaseModel):
    name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    weight: float = 1.0
    normalized_contribution: float = 0.0


class DriftScore(BaseModel):
    agent_id: str
    score: float = Field(ge=0.0, le=1.0, description="Composite drift score 0.0–1.0")
    signals: list[DriftSignal] = Field(default_factory=list)
    sample_count: int = 0
    is_baseline_ready: bool = False
    baseline_version_id: str | None = None
    baseline_status: str | None = None


class BaselineProfile(BaseModel):
    agent_id: str
    metrics: dict[str, dict]  # metric_name -> {mean, std, count}
    sample_count: int
    collection_started_at: str | None = None
    last_updated_at: str | None = None
    baseline_version_id: str | None = None
    baseline_status: str | None = None
    is_governed: bool = False


BaselineVersionStatus = Literal["candidate", "approved", "active", "rejected", "superseded"]


class BaselineProposalRequest(BaseModel):
    window_days: int = Field(default=30, ge=1, le=365)
    notes: str | None = None


class BaselineReviewRequest(BaseModel):
    notes: str | None = None


class BaselineVersionResponse(BaseModel):
    baseline_version_id: str
    agent_id: str
    sample_count: int
    window_days: int
    status: BaselineVersionStatus
    notes: str | None = None
    created_by: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    activated_by: str | None = None
    activated_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    created_at: datetime | None = None
    baseline_data: dict[str, dict] = Field(default_factory=dict)

    model_config = {"from_attributes": True}
