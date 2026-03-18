"""Pillar 4 unit tests: telemetry schema and event building."""
from __future__ import annotations

import pytest

from acr.pillar4_observability.schema import ACRTelemetryEvent
from acr.pillar4_observability.telemetry import build_event
from acr.pillar4_observability.schema import LatencyBreakdown


class TestTelemetrySchema:
    def test_build_allow_event(self) -> None:
        event = build_event(
            event_type="ai_inference",
            agent_id="test-agent",
            agent_purpose="testing",
            agent_capabilities=["tool_a"],
            correlation_id="corr-123",
            session_id="sess-abc",
            tool_name="tool_a",
            parameters={"key": "value"},
            description="Test action",
            context={"actions_this_minute": 1},
            start_time="2026-03-16T00:00:00+00:00",
            end_time="2026-03-16T00:00:00.050+00:00",
            duration_ms=50,
            latency_breakdown=LatencyBreakdown(identity_ms=10, policy_ms=30, total_ms=50),
            policies=[],
            output_decision="allow",
            output_reason=None,
            approval_request_id=None,
            drift_score=None,
        )
        assert event.acr_version == "1.0"
        assert event.event_type == "ai_inference"
        assert event.agent.agent_id == "test-agent"
        assert event.output.decision == "allow"
        assert event.execution.duration_ms == 50

    def test_event_has_uuid_event_id(self) -> None:
        import uuid
        event = build_event(
            event_type="policy_decision",
            agent_id="agent-x",
            agent_purpose="p",
            agent_capabilities=[],
            correlation_id="c",
            session_id=None,
            tool_name=None,
            parameters={},
            description=None,
            context={},
            start_time="2026-01-01T00:00:00+00:00",
            end_time="2026-01-01T00:00:00+00:00",
            duration_ms=0,
            latency_breakdown=LatencyBreakdown(),
            policies=[],
            output_decision="deny",
            output_reason="test",
            approval_request_id=None,
            drift_score=0.5,
        )
        uuid.UUID(event.event_id)  # should not raise
        assert event.metadata.drift_score == 0.5

    def test_event_serializes_to_json(self) -> None:
        event = build_event(
            event_type="ai_inference",
            agent_id="a",
            agent_purpose="p",
            agent_capabilities=[],
            correlation_id="c",
            session_id=None,
            tool_name="tool",
            parameters={},
            description=None,
            context={},
            start_time="2026-01-01T00:00:00+00:00",
            end_time="2026-01-01T00:00:00+00:00",
            duration_ms=5,
            latency_breakdown=LatencyBreakdown(),
            policies=[],
            output_decision="allow",
            output_reason=None,
            approval_request_id=None,
            drift_score=None,
        )
        payload = event.model_dump()
        assert payload["event_type"] == "ai_inference"
        assert "timestamp" in payload
