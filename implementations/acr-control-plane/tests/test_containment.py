"""Pillar 5 unit tests: kill switch state model."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from acr.common.errors import KillSwitchError
from acr.pillar5_containment.killswitch import is_agent_killed
from acr.pillar5_containment.models import ContainmentTier, DRIFT_THRESHOLDS


class TestContainmentModels:
    def test_tier_ordering(self) -> None:
        assert ContainmentTier.NONE < ContainmentTier.THROTTLE
        assert ContainmentTier.THROTTLE < ContainmentTier.RESTRICT
        assert ContainmentTier.RESTRICT < ContainmentTier.ISOLATE
        assert ContainmentTier.ISOLATE < ContainmentTier.KILL

    def test_drift_thresholds_ordered(self) -> None:
        tiers = [ContainmentTier.THROTTLE, ContainmentTier.RESTRICT, ContainmentTier.ISOLATE, ContainmentTier.KILL]
        thresholds = [DRIFT_THRESHOLDS[t] for t in tiers]
        assert thresholds == sorted(thresholds), "Thresholds should be in ascending order"

    def test_kill_threshold_is_highest(self) -> None:
        assert DRIFT_THRESHOLDS[ContainmentTier.KILL] == 0.95


class TestKillSwitchReads:
    async def test_is_agent_killed_fails_secure_without_redis(self) -> None:
        with patch("acr.pillar5_containment.killswitch.get_redis_or_none", return_value=None):
            with pytest.raises(KillSwitchError):
                await is_agent_killed("agent-no-redis")

    async def test_is_agent_killed_fails_secure_on_redis_error(self) -> None:
        redis = AsyncMock()
        redis.hget.side_effect = RuntimeError("redis read failed")

        with patch("acr.pillar5_containment.killswitch.get_redis_or_none", return_value=redis):
            with pytest.raises(KillSwitchError):
                await is_agent_killed("agent-read-error")
