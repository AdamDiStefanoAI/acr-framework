"""Pillar 3: Autonomy Drift Detection — models."""
from __future__ import annotations

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


class BaselineProfile(BaseModel):
    agent_id: str
    metrics: dict[str, dict]  # metric_name -> {mean, std, count}
    sample_count: int
    collection_started_at: str | None = None
    last_updated_at: str | None = None
