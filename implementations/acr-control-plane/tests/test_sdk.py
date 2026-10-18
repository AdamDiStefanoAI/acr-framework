from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock

import httpx
import pytest

from acr.gateway.models import ActionRequest, EvaluateResponse
from acr.pillar1_identity.models import AgentRegisterRequest
from acr.sdk import (
    ACRAgentSession,
    ACRClient,
    ACRDeniedError,
    ACREscalatedError,
    AsyncACRAgentSession,
    AsyncACRClient,
    guard_async_tool,
    guard_tool,
)


def _agent_response_body(agent_id: str) -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "agent_id": agent_id,
        "owner": "support@example.com",
        "purpose": "Handle governed support actions",
        "risk_tier": "medium",
        "allowed_tools": ["query_customer_db", "send_email"],
        "forbidden_tools": ["delete_customer"],
        "data_access": [],
        "boundaries": {
            "max_actions_per_minute": 30,
            "max_cost_per_hour_usd": 5.0,
            "default_action_cost_usd": None,
            "tool_costs_usd": {},
            "allowed_regions": [],
            "credential_rotation_days": 90,
        },
        "is_active": True,
        "version": "1.0.0",
        "parent_agent_id": None,
        "capabilities": [],
        "lifecycle_state": "active",
        "health_status": "healthy",
        "last_heartbeat_at": None,
        "created_at": now,
        "updated_at": now,
    }


def test_sync_client_ensure_agent_registered_fetches_existing_agent() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/acr/agents":
            return httpx.Response(409, json={"detail": "already exists"})
        if request.method == "GET" and request.url.path == "/acr/agents/support-bot":
            return httpx.Response(200, json=_agent_response_body("support-bot"))
        raise AssertionError(f"Unexpected request: {request.method} {request.url.path}")

    client = ACRClient(
        base_url="http://test",
        operator_api_key="operator-key",
        transport=httpx.MockTransport(handler),
    )
    request = AgentRegisterRequest(
        agent_id="support-bot",
        owner="support@example.com",
        purpose="Handle governed support actions",
        allowed_tools=["query_customer_db", "send_email"],
    )

    agent = client.ensure_agent_registered(request)

    assert agent.agent_id == "support-bot"
    assert calls == [("POST", "/acr/agents"), ("GET", "/acr/agents/support-bot")]


@pytest.mark.asyncio
async def test_async_client_can_issue_session_and_evaluate(async_client, sample_agent) -> None:
    sdk = AsyncACRClient(
        base_url="http://test",
        operator_api_key="operator-key",
        client=async_client,
    )

    session = await sdk.issue_agent_session(sample_agent.agent_id)
    result = await session.evaluate_action(
        tool_name="query_customer_db",
        parameters={"customer_id": "C-001"},
        context={"session_id": "sess-sdk-001"},
    )

    assert result.decision == "allow"
    assert result.correlation_id


def test_guard_tool_uses_modified_parameters() -> None:
    class _FakeSession:
        def evaluate_action(self, **kwargs):
            return EvaluateResponse(
                decision="modify",
                modified_action=ActionRequest(
                    tool_name="issue_refund",
                    parameters={"customer_id": kwargs["parameters"]["customer_id"], "amount": 25.0},
                    description=kwargs["description"],
                ),
            )

    def issue_refund(customer_id: str, amount: float) -> dict:
        return {"customer_id": customer_id, "amount": amount}

    guarded = guard_tool(
        issue_refund,
        session=cast(ACRAgentSession, _FakeSession()),
    )

    result = guarded(customer_id="C-100", amount=250.0)

    assert result == {"customer_id": "C-100", "amount": 25.0}


def test_guard_tool_raises_on_deny() -> None:
    class _FakeSession:
        def evaluate_action(self, **kwargs):
            return EvaluateResponse(decision="deny", reason="policy blocked")

    def create_ticket(subject: str) -> dict:
        return {"subject": subject}

    guarded = guard_tool(
        create_ticket,
        session=cast(ACRAgentSession, _FakeSession()),
    )

    with pytest.raises(ACRDeniedError, match="policy blocked"):
        guarded(subject="Escalate to finance")


@pytest.mark.parametrize("status_code", [200, 403])
def test_guard_tool_denies_before_executing_local_tool(status_code: int) -> None:
    tool = Mock(return_value={"status": "executed"})

    def create_ticket(subject: str) -> dict:
        return tool(subject=subject)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/acr/evaluate"
        assert request.headers["Authorization"] == "Bearer agent-token"
        tool.assert_not_called()
        return httpx.Response(status_code, json={"decision": "deny", "reason": "policy blocked"})

    with ACRClient(base_url="http://test", transport=httpx.MockTransport(handler)) as client:
        guarded = guard_tool(
            create_ticket,
            session=client.create_agent_session("support-bot", "agent-token"),
        )

        with pytest.raises(ACRDeniedError, match="policy blocked"):
            guarded(subject="Escalate to finance")

    tool.assert_not_called()


@pytest.mark.asyncio
async def test_guard_async_tool_does_not_execute_on_deny() -> None:
    calls: list[str] = []

    class _FakeAsyncSession:
        async def evaluate_action(self, **kwargs):
            return EvaluateResponse(decision="deny", reason="policy blocked")

    async def create_ticket(subject: str) -> dict:
        calls.append(subject)
        return {"subject": subject}

    guarded = guard_async_tool(
        create_ticket,
        session=cast(AsyncACRAgentSession, _FakeAsyncSession()),
    )

    with pytest.raises(ACRDeniedError, match="policy blocked"):
        await guarded(subject="Escalate to finance")

    assert calls == []


@pytest.mark.asyncio
async def test_guard_async_tool_returns_execution_result_without_local_call() -> None:
    class _FakeAsyncSession:
        async def evaluate_action(self, **kwargs):
            return EvaluateResponse(
                decision="allow",
                execution_result={"status": "executed-by-gateway", "tool": kwargs["tool_name"]},
            )

    async def send_email(to: str, subject: str) -> dict:
        raise AssertionError("local tool should not execute when execution_result is returned")

    guarded = guard_async_tool(
        send_email,
        session=cast(AsyncACRAgentSession, _FakeAsyncSession()),
        execute_locally_on_allow=False,
    )

    result = await guarded(to="alice@example.com", subject="Status update")

    assert result == {"status": "executed-by-gateway", "tool": "send_email"}


@pytest.mark.asyncio
async def test_guard_async_tool_raises_on_escalate() -> None:
    class _FakeAsyncSession:
        async def evaluate_action(self, **kwargs):
            return EvaluateResponse(
                decision="escalate",
                reason="manager approval required",
                approval_request_id="apr_123",
            )

    async def send_email(to: str, subject: str) -> dict:
        return {"to": to, "subject": subject}

    guarded = guard_async_tool(
        send_email,
        session=cast(AsyncACRAgentSession, _FakeAsyncSession()),
    )

    with pytest.raises(ACREscalatedError, match="manager approval required"):
        await guarded(to="alice@example.com", subject="Status update")
