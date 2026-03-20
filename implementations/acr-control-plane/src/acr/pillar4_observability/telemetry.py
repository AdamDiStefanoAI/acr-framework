"""Pillar 4: Structured JSON telemetry event generation and persistence."""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from acr.config import settings
from acr.db.models import TelemetryEventRecord
from acr.pillar4_observability.schema import (
    ACRTelemetryEvent,
    AcrControlPlaneMetadata,
    AgentTelemetryObject,
    EventType,
    ExecutionObject,
    LatencyBreakdown,
    OutputObject,
    PolicyResult,
    RequestTelemetryObject,
    TelemetryMetadata,
)

logger = structlog.get_logger(__name__)


def build_event(
    *,
    event_type: EventType,
    agent_id: str,
    agent_purpose: str,
    agent_capabilities: list[str],
    correlation_id: str,
    session_id: str | None,
    tool_name: str | None,
    parameters: dict,
    description: str | None,
    context: dict,
    intent: dict,
    start_time: str,
    end_time: str,
    duration_ms: int,
    latency_breakdown: LatencyBreakdown,
    policies: list[PolicyResult],
    output_decision: str,
    output_reason: str | None,
    approval_request_id: str | None,
    drift_score: float | None,
    custom: dict | None = None,
) -> ACRTelemetryEvent:
    return ACRTelemetryEvent(
        event_type=event_type,
        agent=AgentTelemetryObject(
            agent_id=agent_id,
            purpose=agent_purpose,
            capabilities=agent_capabilities,
        ),
        request=RequestTelemetryObject(
            request_id=correlation_id,
            session_id=session_id,
            tool_name=tool_name,
            parameters=parameters,
            description=description,
            context=context,
            intent=intent,
        ),
        execution=ExecutionObject(
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            latency_breakdown=latency_breakdown,
        ),
        policies=policies,
        output=OutputObject(
            decision=output_decision,  # type: ignore[arg-type]
            reason=output_reason,
            approval_request_id=approval_request_id,
        ),
        metadata=TelemetryMetadata(
            environment=settings.acr_env,
            acr_control_plane=AcrControlPlaneMetadata(version=settings.acr_version),
            drift_score=drift_score,
        ),
        custom=custom or {},
    )


async def persist_event(db: AsyncSession, event: ACRTelemetryEvent) -> None:
    """Write the telemetry event to PostgreSQL (async, non-blocking in background task)."""
    record = TelemetryEventRecord(
        event_id=event.event_id,
        correlation_id=event.request.request_id,
        event_type=event.event_type,
        agent_id=event.agent.agent_id,
        payload=event.model_dump(),
    )
    db.add(record)
    await db.flush()


def log_event(event: ACRTelemetryEvent) -> None:
    """Emit the event as a structured JSON log line."""
    logger.info(
        "acr_event",
        acr_version=event.acr_version,
        event_id=event.event_id,
        event_type=event.event_type,
        correlation_id=event.request.request_id,
        agent_id=event.agent.agent_id,
        tool_name=event.request.tool_name,
        decision=event.output.decision,
        duration_ms=event.execution.duration_ms,
        drift_score=event.metadata.drift_score,
    )
