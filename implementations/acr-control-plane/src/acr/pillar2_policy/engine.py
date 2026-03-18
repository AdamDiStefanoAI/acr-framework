"""Pillar 2: OPA policy engine client."""
from __future__ import annotations

import asyncio
import time

import httpx
import structlog

from acr.common.errors import PolicyEngineError
from acr.config import settings
from acr.pillar2_policy.models import PolicyDecision, PolicyEvaluationResult

logger = structlog.get_logger(__name__)

# Separate connect / read timeouts; keeps hot-path latency predictable.
_TIMEOUT = httpx.Timeout(timeout=3.0, connect=2.0)

# Retry config: up to 3 attempts with exponential back-off.
# Only retried on transient network/5xx errors, never on 4xx.
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.05  # seconds; doubles each attempt → 50ms, 100ms, 200ms

# HTTP status codes that are worth retrying (transient server-side failures)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


async def evaluate_policy(
    agent_manifest: dict,
    action: dict,
    context: dict,
) -> PolicyEvaluationResult:
    """
    Send action context to OPA and parse allow/deny/escalate decision.
    Targets <100ms at P95.

    Retries up to 3 times on transient errors. Raises PolicyEngineError
    (fail-secure) if all attempts fail — the gateway then denies the action.
    """
    start_ms = time.monotonic()

    # Inject safe defaults so missing context keys never bypass policy checks.
    # The gateway already sets actions_this_minute from the server-side counter,
    # but this guards against any caller that builds context manually.
    safe_context = {
        "actions_this_minute": 0,
        "hourly_spend_usd": 0.0,
        **context,  # caller's real values override the defaults
    }

    opa_input = {
        "input": {
            "agent": agent_manifest,
            "action": action,
            "context": safe_context,
        }
    }

    last_exc: Exception | None = None
    data: dict = {}

    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(base_url=settings.opa_url, timeout=_TIMEOUT) as client:
                resp = await client.post("/v1/data/acr", json=opa_input)

            # Don't retry client errors (4xx) — they signal bad input, not OPA failure
            if 400 <= resp.status_code < 500 and resp.status_code not in _RETRYABLE_STATUS:
                resp.raise_for_status()

            if resp.status_code in _RETRYABLE_STATUS:
                raise httpx.HTTPStatusError(
                    f"OPA returned HTTP {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )

            resp.raise_for_status()
            data = resp.json()
            break  # success — exit retry loop

        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "opa_retry",
                    attempt=attempt + 1,
                    delay_s=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
    else:
        # All retries exhausted — fail-secure
        raise PolicyEngineError(
            f"OPA unreachable after {_MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    elapsed_ms = int((time.monotonic() - start_ms) * 1000)

    # Defensive: treat missing/null `result` as empty (deny-by-default still applies)
    result = data.get("result") or {}

    # Parse OPA result structure:
    # result.allow = bool
    # result.deny = list[str]  (denial reasons)
    # result.escalate = bool
    # result.escalate_queue = str
    # result.escalate_sla_minutes = int

    deny_reasons: list[str] = result.get("deny", [])
    allow: bool = result.get("allow", False)
    escalate: bool = result.get("escalate", False)
    escalate_queue: str = result.get("escalate_queue", "default")
    escalate_sla: int = result.get("escalate_sla_minutes", 240)

    decisions: list[PolicyDecision] = []

    if deny_reasons:
        final = "deny"
        reason = "; ".join(deny_reasons)
        for i, r in enumerate(deny_reasons):
            decisions.append(PolicyDecision(
                policy_id=f"acr-deny-{i}",
                decision="deny",
                reason=r,
                latency_ms=elapsed_ms,
            ))
    elif escalate:
        final = "escalate"
        reason = f"Action requires human approval (queue: {escalate_queue})"
        decisions.append(PolicyDecision(
            policy_id="acr-escalate",
            decision="escalate",
            reason=reason,
            latency_ms=elapsed_ms,
        ))
    elif allow:
        final = "allow"
        reason = None
        decisions.append(PolicyDecision(
            policy_id="acr-allow",
            decision="allow",
            latency_ms=elapsed_ms,
        ))
    else:
        # OPA returned neither allow=true nor deny=[...] — fail-secure: deny
        final = "deny"
        reason = "Policy did not explicitly allow this action (deny-by-default)"
        decisions.append(PolicyDecision(
            policy_id="acr-default-deny",
            decision="deny",
            reason=reason,
            latency_ms=elapsed_ms,
        ))

    logger.debug(
        "opa_evaluation",
        final=final,
        latency_ms=elapsed_ms,
        deny_reasons=deny_reasons,
        escalate=escalate,
    )

    return PolicyEvaluationResult(
        final_decision=final,  # type: ignore[arg-type]
        decisions=decisions,
        reason=reason,
        approval_queue=escalate_queue if escalate else None,
        sla_minutes=escalate_sla if escalate else None,
        latency_ms=elapsed_ms,
    )
