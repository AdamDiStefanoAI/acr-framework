"""Pillar 6: Approval queue logic — create, approve, deny, timeout, override."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import timedelta

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import ApprovalNotFoundError
from acr.common.time import utcnow
from acr.config import settings
from acr.db.models import ApprovalRequestRecord
from acr.gateway.executor import execute_action

logger = structlog.get_logger(__name__)


def _sign_payload(payload: dict) -> str:
    """
    Compute HMAC-SHA256 over the canonical JSON of a webhook payload.
    Returns hex digest. Receivers should verify:
        hmac.compare_digest(expected_sig, X-ACR-Signature header value)
    """
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        settings.webhook_hmac_secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()


async def create_approval_request(
    db: AsyncSession,
    *,
    correlation_id: str,
    agent_id: str,
    tool_name: str,
    parameters: dict,
    description: str | None,
    approval_queue: str,
    sla_minutes: int,
) -> ApprovalRequestRecord:
    """Insert a new approval request and optionally fire a webhook."""
    request_id = f"apr-{uuid.uuid4()}"
    expires_at = utcnow() + timedelta(minutes=sla_minutes) if sla_minutes > 0 else None

    record = ApprovalRequestRecord(
        request_id=request_id,
        correlation_id=correlation_id,
        agent_id=agent_id,
        tool_name=tool_name,
        parameters=parameters,
        description=description,
        approval_queue=approval_queue,
        sla_minutes=sla_minutes,
        expires_at=expires_at,
        status="pending",
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info(
        "approval_request_created",
        request_id=request_id,
        agent_id=agent_id,
        tool_name=tool_name,
        queue=approval_queue,
        sla_minutes=sla_minutes,
    )

    # Fire webhook notification (fire-and-forget)
    if settings.webhook_url:
        webhook_payload = {
            "event": "approval_request_created",
            "request_id": request_id,
            # idempotency_key lets receivers deduplicate retried deliveries.
            # Derived deterministically from correlation_id so retries produce the same key.
            "idempotency_key": correlation_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "queue": approval_queue,
            "sla_minutes": sla_minutes,
        }
        headers: dict[str, str] = {}
        if settings.webhook_hmac_secret:
            headers["X-ACR-Signature"] = _sign_payload(webhook_payload)
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(
                    settings.webhook_url,
                    json=webhook_payload,
                    headers=headers,
                )
        except Exception as exc:
            logger.warning("webhook_failed", url=settings.webhook_url, error=str(exc))

    return record


async def get_approval_request(db: AsyncSession, request_id: str) -> ApprovalRequestRecord:
    result = await db.execute(
        select(ApprovalRequestRecord).where(ApprovalRequestRecord.request_id == request_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise ApprovalNotFoundError(f"Approval request '{request_id}' not found")
    return record


async def list_pending_approvals(db: AsyncSession) -> list[ApprovalRequestRecord]:
    result = await db.execute(
        select(ApprovalRequestRecord)
        .where(ApprovalRequestRecord.status == "pending")
        .order_by(ApprovalRequestRecord.created_at.asc())
    )
    return list(result.scalars().all())


async def approve(db: AsyncSession, request_id: str, decided_by: str, reason: str | None) -> ApprovalRequestRecord:
    record = await get_approval_request(db, request_id)
    record.status = "approved"
    record.decision = "approved"
    record.decided_by = decided_by
    record.decision_reason = reason
    record.decided_at = utcnow()
    await db.flush()
    logger.info("approval_approved", request_id=request_id, decided_by=decided_by)
    return record


async def deny(db: AsyncSession, request_id: str, decided_by: str, reason: str | None) -> ApprovalRequestRecord:
    record = await get_approval_request(db, request_id)
    record.status = "denied"
    record.decision = "denied"
    record.decided_by = decided_by
    record.decision_reason = reason
    record.decided_at = utcnow()
    await db.flush()
    logger.info("approval_denied", request_id=request_id, decided_by=decided_by)
    return record


async def override(db: AsyncSession, request_id: str, decided_by: str, reason: str) -> ApprovalRequestRecord:
    """Break-glass override — always logs operator identity and reason."""
    record = await get_approval_request(db, request_id)
    record.status = "overridden"
    record.decision = "overridden"
    record.decided_by = decided_by
    record.decision_reason = reason
    record.decided_at = utcnow()
    await db.flush()
    logger.warning(
        "approval_break_glass_override",
        request_id=request_id,
        decided_by=decided_by,
        reason=reason,
    )
    return record


async def execute_approval(record: ApprovalRequestRecord) -> dict:
    """Execute an approved/overridden action when downstream execution is enabled."""
    result = await execute_action(
        agent_id=record.agent_id,
        tool_name=record.tool_name,
        parameters=record.parameters or {},
        description=record.description,
        correlation_id=record.correlation_id,
        approval_request_id=record.request_id,
    )
    record.execution_result = result
    logger.info(
        "approval_executed",
        request_id=record.request_id,
        agent_id=record.agent_id,
        tool_name=record.tool_name,
    )
    return result


async def expire_timed_out_approvals(db: AsyncSession) -> int:
    """Mark expired pending approvals as timed_out. Returns count updated."""
    now = utcnow()
    result = await db.execute(
        select(ApprovalRequestRecord).where(
            ApprovalRequestRecord.status == "pending",
            ApprovalRequestRecord.expires_at <= now,
        )
    )
    records = result.scalars().all()
    count = 0
    for record in records:
        record.status = "timed_out"
        record.decision = "denied"
        record.decision_reason = "Approval SLA expired — auto-denied"
        record.decided_at = now
        count += 1
    if count:
        await db.flush()
        logger.info("approvals_timed_out", count=count)
    return count
