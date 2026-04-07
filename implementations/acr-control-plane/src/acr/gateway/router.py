"""
Gateway router: POST /acr/evaluate — the main gateway endpoint.

Synchronous pipeline (<200ms budget):
  [1] Kill switch — direct Redis read
  [2] Identity check — validate agent exists and is active
  [3] Rate limit — server-side Redis counter (overrides self-reported context)
  [4] Policy evaluation — OPA allow/deny/escalate
  [5] Output filter — PII redaction on parameters
  [6] (if escalate) Approval queue creation

Async background tasks (non-blocking):
  [7] Telemetry persistence
  [8] Drift metric sample recording
  [9] Drift score computation + graduated response check
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from acr.common.correlation import get_correlation_id
from acr.common.errors import (
    ACRError,
    AgentKilledError,
    AgentNotRegisteredError,
    PolicyEngineError,
)
from acr.common.redis_client import get_redis_or_none
from acr.common.time import iso_utcnow
from acr.config import settings
from acr.db.database import BackgroundSessionLocal, async_session_factory, get_db
from acr.gateway.auth import require_agent_token
from acr.gateway.executor import execute_action
from acr.pillar1_identity.registry import get_manifest
from acr.pillar1_identity.validator import validate_agent_identity
from acr.pillar2_policy.engine import evaluate_policy
from acr.pillar2_policy.output_filter import filter_parameters
from acr.pillar3_drift.baseline import record_metric_sample
from acr.pillar4_observability.otel import acr_span, get_meter
from acr.pillar4_observability.schema import LatencyBreakdown, PolicyResult
from acr.pillar4_observability.telemetry import build_event, log_event, persist_event
from acr.pillar5_containment.graduated import _ISOLATE_PREFIX, _RESTRICT_PREFIX, _THROTTLE_PREFIX
from acr.pillar5_containment.killswitch import is_agent_killed
from acr.pillar6_authority.approval import create_approval_request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/acr", tags=["Gateway"])

# Redis key prefix for server-side rate limit counters
_RATE_KEY_PREFIX = "acr:rate:"
# Redis key prefix for cached drift scores
_DRIFT_SCORE_PREFIX = "acr:drift:score:"
# Drift check runs at most once per N evaluations per agent (avoids DB hit every call)
_DRIFT_CHECK_EVERY_N = 10


# ── Request / Response models ─────────────────────────────────────────────────

class ActionRequest(BaseModel):
    tool_name: str
    parameters: dict = Field(default_factory=dict)
    description: str | None = None


class IntentRequest(BaseModel):
    goal: str | None = None
    justification: str | None = None
    expected_effects: list[str] = Field(default_factory=list)
    requested_by_step: str | None = None
    metadata: dict = Field(default_factory=dict)


class EvaluateRequest(BaseModel):
    agent_id: str
    action: ActionRequest
    context: dict = Field(default_factory=dict)
    intent: IntentRequest | None = None


# ── Background tasks ──────────────────────────────────────────────────────────

async def _record_drift_sample(
    agent_id: str,
    tool_name: str,
    policy_denied: bool,
    latency_ms: int,
    correlation_id: str,
) -> None:
    async with BackgroundSessionLocal() as db:
        try:
            await record_metric_sample(
                db,
                agent_id=agent_id,
                correlation_id=correlation_id,
                tool_name=tool_name,
                action_type=tool_name,
                policy_denied=policy_denied,
                latency_ms=latency_ms,
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Background drift sample failed", error=str(exc), exc_info=True)


async def _run_drift_check(agent_id: str) -> None:
    """Compute drift score and apply graduated response. Caches result to Redis."""
    from acr.pillar3_drift.detector import run_drift_check

    async with BackgroundSessionLocal() as db:
        try:
            drift = await run_drift_check(db, agent_id)
            await db.commit()
            # Cache drift score for fast reads in subsequent responses
            redis = get_redis_or_none()
            if redis and drift.is_baseline_ready:
                await redis.setex(
                    f"{_DRIFT_SCORE_PREFIX}{agent_id}",
                    300,  # 5-minute TTL
                    str(drift.score),
                )
        except Exception as exc:
            await db.rollback()
            logger.error("Background drift check failed", error=str(exc), exc_info=True)


async def _persist_telemetry(event_dict: dict) -> None:
    from acr.pillar4_observability.schema import ACRTelemetryEvent

    async with BackgroundSessionLocal() as db:
        try:
            event = ACRTelemetryEvent.model_validate(event_dict)
            await persist_event(db, event)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Background telemetry persist failed", error=str(exc), exc_info=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_rate_count(agent_id: str) -> int:
    """Increment and return the server-side action counter for this agent/minute."""
    redis = get_redis_or_none()
    if redis is None:
        return 0
    now = datetime.now(timezone.utc)
    minute_bucket = now.strftime("%Y%m%d%H%M")
    key = f"{_RATE_KEY_PREFIX}{agent_id}:{minute_bucket}"
    try:
        count = await redis.incr(key)
        await redis.expire(key, 120)  # expire after 2 minutes
        return count
    except Exception:
        return 0


async def _get_cached_drift_score(agent_id: str) -> float | None:
    redis = get_redis_or_none()
    if redis is None:
        return None
    try:
        val = await redis.get(f"{_DRIFT_SCORE_PREFIX}{agent_id}")
        return float(val) if val else None
    except Exception:
        return None


async def _should_run_drift_check(agent_id: str) -> bool:
    """Return True every N-th call to throttle DB drift computations."""
    redis = get_redis_or_none()
    if redis is None:
        return False
    key = f"acr:drift:counter:{agent_id}"
    try:
        n = await redis.incr(key)
        await redis.expire(key, 3600)
        return (n % _DRIFT_CHECK_EVERY_N) == 0
    except Exception:
        return False


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate(
    req: EvaluateRequest,
    background_tasks: BackgroundTasks,
    authorized_agent_id: str = Depends(require_agent_token),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    ACR Gateway — the central control plane decision point.
    All agent action requests flow through here.

    Requires a valid Bearer JWT issued by POST /acr/agents/{id}/token.
    The JWT's `sub` claim must match the `agent_id` in the request body.
    """
    correlation_id = get_correlation_id()
    start_time = iso_utcnow()
    t_start = time.monotonic()
    identity_ms = policy_ms = 0

    try:
        # ── [0] Token / body agent_id consistency check ───────────────────────
        # Prevents one agent from submitting actions on behalf of another.
        if authorized_agent_id != req.agent_id:
            return JSONResponse(
                status_code=403,
                content={
                    "decision": "deny",
                    "error_code": "AGENT_ID_MISMATCH",
                    "reason": "Token subject does not match request agent_id",
                },
            )

        # ── [1] Kill switch check (Redis direct read, ~0.5ms) ─────────────────
        if await is_agent_killed(req.agent_id):
            raise AgentKilledError(f"Agent '{req.agent_id}' is killed")

        # ── [1b] Graduated containment enforcement (Redis reads) ─────────────
        # These keys are written by the drift-scoring background worker in
        # graduated.py when an agent's drift score crosses a tier threshold.
        redis = get_redis_or_none()
        if redis is not None:
            # Tier 3 — Isolate: override every decision to escalate
            isolate_val = await redis.get(f"{_ISOLATE_PREFIX}{req.agent_id}")
            if isolate_val == "1":
                return JSONResponse(
                    status_code=202,
                    content={
                        "decision": "escalate",
                        "correlation_id": correlation_id,
                        "reason": "agent_isolated_all_actions_require_approval",
                    },
                )

            # Tier 2 — Restrict: only whitelisted tools are allowed
            restrict_val = await redis.get(f"{_RESTRICT_PREFIX}{req.agent_id}")
            if restrict_val is not None:
                import json as _json
                allowed_tools = _json.loads(restrict_val)
                if req.action.tool_name not in allowed_tools:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "decision": "deny",
                            "correlation_id": correlation_id,
                            "reason": "agent_restricted_tool_not_allowed",
                        },
                    )

            # Tier 1 — Throttle: reduce effective rate limit by the throttle %
            throttle_val = await redis.get(f"{_THROTTLE_PREFIX}{req.agent_id}")
            if throttle_val is not None:
                throttle_pct = int(throttle_val)
                # We apply the throttle in step [3] by scaling the effective limit.
                # Store for later use.
                enriched_context_throttle_pct = throttle_pct
            else:
                enriched_context_throttle_pct = 100
        else:
            enriched_context_throttle_pct = 100

        # ── [2] Identity check ────────────────────────────────────────────────
        with acr_span("identity_check", {"agent.id": req.agent_id}):
            t0 = time.monotonic()
            agent_record = await validate_agent_identity(db, req.agent_id)
            manifest = await get_manifest(db, req.agent_id)
            identity_ms = int((time.monotonic() - t0) * 1000)

        # ── [3] Server-side rate limit counter ────────────────────────────────
        # Override self-reported count with the authoritative server-side value.
        # When Tier 1 (throttle) is active the effective count is scaled up so
        # the agent hits its limit sooner (e.g. 50% throttle → count * 2).
        server_count = await _get_rate_count(req.agent_id)
        if enriched_context_throttle_pct < 100:
            effective_count = int(server_count * (100 / enriched_context_throttle_pct))
        else:
            effective_count = server_count
        enriched_context = {**req.context, "actions_this_minute": effective_count}

        # ── [4] Policy evaluation (OPA) ───────────────────────────────────────
        with acr_span("policy_evaluation", {"agent.id": req.agent_id, "action.tool": req.action.tool_name}):
            t0 = time.monotonic()
            policy_result = await evaluate_policy(
                agent_manifest=manifest.model_dump(),
                action=req.action.model_dump(),
                context=enriched_context,
            )
            policy_ms = int((time.monotonic() - t0) * 1000)

        # ── [5] Output filter — PII redaction ─────────────────────────────────
        filtered_params = filter_parameters(
            req.action.tool_name,
            req.action.parameters,
            correlation_id,
        )

        total_ms = int((time.monotonic() - t_start) * 1000)
        end_time = iso_utcnow()

        telemetry_policies = [
            PolicyResult(
                policy_id=d.policy_id,
                decision=d.decision,  # type: ignore[arg-type]
                reason=d.reason,
                latency_ms=d.latency_ms,
            )
            for d in policy_result.decisions
        ]

        # Fetch cached drift score for inclusion in response
        drift_score = await _get_cached_drift_score(req.agent_id)

        # Record OTEL metrics for all decisions
        _record_evaluate_metrics(req.agent_id, policy_result.final_decision, total_ms)

        # ── [6] Escalate → approval queue ─────────────────────────────────────
        if policy_result.final_decision == "escalate":
            approval = await create_approval_request(
                db,
                correlation_id=correlation_id,
                agent_id=req.agent_id,
                tool_name=req.action.tool_name,
                parameters=filtered_params,
                description=req.action.description,
                approval_queue=policy_result.approval_queue or "default",
                sla_minutes=policy_result.sla_minutes or 240,
            )
            _queue_background_tasks(
                background_tasks,
                agent_id=req.agent_id,
                tool_name=req.action.tool_name,
                policy_denied=False,
                total_ms=total_ms,
                correlation_id=correlation_id,
                event_kwargs=dict(
                    event_type="ai_inference",
                    manifest=manifest,
                    correlation_id=correlation_id,
                    req=req,
                    filtered_params=filtered_params,
                    start_time=start_time,
                    end_time=end_time,
                    total_ms=total_ms,
                    identity_ms=identity_ms,
                    policy_ms=policy_ms,
                    telemetry_policies=telemetry_policies,
                    output_decision="escalate",
                    output_reason=policy_result.reason,
                    approval_request_id=approval.request_id,
                    drift_score=drift_score,
                ),
            )
            return JSONResponse(
                status_code=202,
                content={
                    "decision": "escalate",
                    "correlation_id": correlation_id,
                    "approval_request_id": approval.request_id,
                    "reason": policy_result.reason,
                    "approval_queue": approval.approval_queue,
                    "sla_minutes": approval.sla_minutes,
                },
            )

        # ── [7] Deny ──────────────────────────────────────────────────────────
        if policy_result.final_decision == "deny":
            _queue_background_tasks(
                background_tasks,
                agent_id=req.agent_id,
                tool_name=req.action.tool_name,
                policy_denied=True,
                total_ms=total_ms,
                correlation_id=correlation_id,
                event_kwargs=dict(
                    event_type="policy_decision",
                    manifest=manifest,
                    correlation_id=correlation_id,
                    req=req,
                    filtered_params=filtered_params,
                    start_time=start_time,
                    end_time=end_time,
                    total_ms=total_ms,
                    identity_ms=identity_ms,
                    policy_ms=policy_ms,
                    telemetry_policies=telemetry_policies,
                    output_decision="deny",
                    output_reason=policy_result.reason,
                    approval_request_id=None,
                    drift_score=drift_score,
                ),
            )
            return JSONResponse(
                status_code=403,
                content={
                    "decision": "deny",
                    "correlation_id": correlation_id,
                    "reason": policy_result.reason,
                    "policy_decisions": [
                        {"policy_id": d.policy_id, "decision": d.decision, "reason": d.reason}
                        for d in policy_result.decisions
                    ],
                },
            )

        # ── [8] Allow ─────────────────────────────────────────────────────────
        execution_result = None
        if settings.execute_allowed_actions:
            execution_result = await execute_action(
                agent_id=req.agent_id,
                tool_name=req.action.tool_name,
                parameters=req.action.parameters,
                description=req.action.description,
                correlation_id=correlation_id,
            )
        _queue_background_tasks(
            background_tasks,
            agent_id=req.agent_id,
            tool_name=req.action.tool_name,
            policy_denied=False,
            total_ms=total_ms,
            correlation_id=correlation_id,
            event_kwargs=dict(
                event_type="ai_inference",
                manifest=manifest,
                correlation_id=correlation_id,
                req=req,
                filtered_params=filtered_params,
                start_time=start_time,
                end_time=end_time,
                total_ms=total_ms,
                identity_ms=identity_ms,
                policy_ms=policy_ms,
                telemetry_policies=telemetry_policies,
                output_decision="allow",
                output_reason=None,
                approval_request_id=None,
                drift_score=drift_score,
            ),
        )
        content = {
            "decision": "allow",
            "correlation_id": correlation_id,
            "policy_decisions": [
                {"policy_id": d.policy_id, "decision": d.decision}
                for d in policy_result.decisions
            ],
            "drift_score": drift_score,
            "latency_ms": total_ms,
        }
        if execution_result is not None:
            content["execution_result"] = execution_result
        return JSONResponse(status_code=200, content=content)

    except AgentKilledError as exc:
        return JSONResponse(status_code=403, content={"decision": "deny", "reason": exc.message, "error_code": exc.error_code})
    except AgentNotRegisteredError as exc:
        return JSONResponse(status_code=403, content={"decision": "deny", "reason": exc.message, "error_code": exc.error_code})
    except PolicyEngineError as exc:
        # Fail-secure: OPA down → deny
        return JSONResponse(status_code=503, content={"decision": "deny", "reason": f"Policy engine unavailable: {exc.message}", "error_code": exc.error_code})
    except ACRError as exc:
        return JSONResponse(status_code=exc.status_code, content={"decision": "deny", "reason": exc.message, "error_code": exc.error_code})
    except Exception:
        # Fail-secure: never expose stack traces to clients
        return JSONResponse(status_code=500, content={"decision": "deny", "reason": "Internal control plane error", "error_code": "INTERNAL_ERROR"})


# ── OTEL metrics helper ──────────────────────────────────────────────────────

def _record_evaluate_metrics(agent_id: str, decision: str, latency_ms: int) -> None:
    """Increment OTLP counters/histograms for each evaluate call."""
    meter = get_meter()
    meter.create_counter("acr.evaluate.total").add(
        1, {"agent_id": agent_id, "decision": decision}
    )
    meter.create_histogram("acr.evaluate.latency", unit="ms").record(
        latency_ms, {"agent_id": agent_id}
    )


# ── Background task helpers ───────────────────────────────────────────────────

def _queue_background_tasks(
    background_tasks: BackgroundTasks,
    *,
    agent_id: str,
    tool_name: str,
    policy_denied: bool,
    total_ms: int,
    correlation_id: str,
    event_kwargs: dict,
) -> None:
    """Queue all post-response background work."""
    background_tasks.add_task(
        _emit_telemetry_event,
        **event_kwargs,
    )
    background_tasks.add_task(
        _record_drift_sample,
        agent_id,
        tool_name,
        policy_denied,
        total_ms,
        correlation_id,
    )
    background_tasks.add_task(_maybe_run_drift_check, agent_id)


async def _maybe_run_drift_check(agent_id: str) -> None:
    """Run drift check only every N evaluations to avoid hammering the DB."""
    if await _should_run_drift_check(agent_id):
        await _run_drift_check(agent_id)


async def _emit_telemetry_event(
    *,
    event_type,
    manifest,
    correlation_id,
    req,
    filtered_params,
    start_time,
    end_time,
    total_ms,
    identity_ms,
    policy_ms,
    telemetry_policies,
    output_decision,
    output_reason,
    approval_request_id,
    drift_score,
) -> None:
    event = build_event(
        event_type=event_type,
        agent_id=manifest.agent_id,
        agent_purpose=manifest.purpose,
        agent_capabilities=manifest.allowed_tools,
        correlation_id=correlation_id,
        session_id=req.context.get("session_id"),
        tool_name=req.action.tool_name,
        parameters=filtered_params,
        description=req.action.description,
        context=req.context,
        intent=req.intent.model_dump(exclude_none=True) if req.intent else {},
        start_time=start_time,
        end_time=end_time,
        duration_ms=total_ms,
        latency_breakdown=LatencyBreakdown(identity_ms=identity_ms, policy_ms=policy_ms, total_ms=total_ms),
        policies=telemetry_policies,
        output_decision=output_decision,
        output_reason=output_reason,
        approval_request_id=approval_request_id,
        drift_score=drift_score,
    )
    log_event(event)
    await _persist_telemetry(event.model_dump(mode="json"))
