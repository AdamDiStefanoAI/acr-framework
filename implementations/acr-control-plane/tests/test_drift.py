"""Pillar 3 unit tests: drift signals and scoring."""
from __future__ import annotations

import pytest

from acr.pillar3_drift.models import DriftSignal
from acr.pillar3_drift.signals import (
    RawMetrics,
    composite_drift_score,
    compute_signals,
    compute_z_score,
    z_to_drift_contribution,
)


class TestDriftSignals:
    def test_z_score_zero_std(self) -> None:
        # Zero std → 0 z-score (no division by zero)
        assert compute_z_score(5.0, 5.0, 0.0) == 0.0

    def test_z_score_positive(self) -> None:
        z = compute_z_score(10.0, 5.0, 2.5)
        assert z == pytest.approx(2.0)

    def test_z_to_contribution_capped(self) -> None:
        # z=5 → 1.0, z=0 → 0.0
        assert z_to_drift_contribution(5.0) == pytest.approx(1.0)
        assert z_to_drift_contribution(0.0) == pytest.approx(0.0)

    def test_composite_score_zero_when_nominal(self) -> None:
        # All metrics at baseline mean → 0 drift
        metrics = RawMetrics(
            tool_calls_per_minute=5.0,
            denial_rate=0.02,
            error_rate=0.01,
            action_diversity=0.7,
        )
        baseline = {
            "tool_call_frequency": {"mean": 5.0, "std": 1.0},
            "denial_rate": {"mean": 0.02, "std": 0.01},
            "error_rate": {"mean": 0.01, "std": 0.005},
            "action_diversity": {"mean": 0.7, "std": 0.1},
        }
        signals = compute_signals(metrics, baseline)
        score = composite_drift_score(signals)
        assert score < 0.05  # should be very close to 0

    def test_composite_score_high_on_anomaly(self) -> None:
        # Denial rate 100x higher than baseline
        metrics = RawMetrics(
            tool_calls_per_minute=5.0,
            denial_rate=0.95,   # anomalous
            error_rate=0.01,
            action_diversity=0.7,
        )
        baseline = {
            "tool_call_frequency": {"mean": 5.0, "std": 1.0},
            "denial_rate": {"mean": 0.02, "std": 0.01},
            "error_rate": {"mean": 0.01, "std": 0.005},
            "action_diversity": {"mean": 0.7, "std": 0.1},
        }
        signals = compute_signals(metrics, baseline)
        score = composite_drift_score(signals)
        assert score > 0.3  # should be significantly elevated


class TestContainmentTiers:
    def test_tier_thresholds(self) -> None:
        from acr.pillar5_containment.graduated import tier_for_score
        from acr.pillar5_containment.models import ContainmentTier

        assert tier_for_score(0.5) == ContainmentTier.NONE
        assert tier_for_score(0.6) == ContainmentTier.THROTTLE
        assert tier_for_score(0.7) == ContainmentTier.RESTRICT
        assert tier_for_score(0.85) == ContainmentTier.ISOLATE
        assert tier_for_score(0.95) == ContainmentTier.KILL
        assert tier_for_score(1.0) == ContainmentTier.KILL
