"""Exercise the public sync/async SDK contracts without a running API server."""

from __future__ import annotations

import inspect
import json
from contextlib import asynccontextmanager

import httpx
import pytest

from acr.gateway.models import ActionRequest, EvaluateRequest
from acr.pillar1_identity.models import AgentRegisterRequest
from acr.sdk import ACRClient, ACRHTTPError, AsyncACRClient


@pytest.fixture(params=[ACRClient, AsyncACRClient], ids=["sync", "async"])
def client_type(request):
    return request.param


async def _resolve(result):
    return await result if inspect.isawaitable(result) else result


@asynccontextmanager
async def _sdk(client_type, handler, **kwargs):
    client = client_type(
        base_url="https://control.example/", transport=httpx.MockTransport(handler), **kwargs
    )
    if isinstance(client, AsyncACRClient):
        async with client:
            yield client
    else:
        with client:
            yield client


def _agent_body() -> dict:
    return {
        "agent_id": "support-bot",
        "owner": "support@example.com",
        "purpose": "Answer support questions",
        "risk_tier": "medium",
        "allowed_tools": ["create_ticket"],
        "forbidden_tools": [],
        "data_access": [],
        "boundaries": {},
        "is_active": True,
        "version": "1.0.0",
        "parent_agent_id": None,
        "capabilities": [],
        "lifecycle_state": "active",
        "health_status": "healthy",
        "last_heartbeat_at": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _registration() -> AgentRegisterRequest:
    return AgentRegisterRequest(
        agent_id="support-bot",
        owner="support@example.com",
        purpose="Answer support questions",
        allowed_tools=["create_ticket"],
    )


@pytest.mark.parametrize("ensure", [False, True], ids=["register", "ensure"])
async def test_registration_serializes_request_and_operator_auth(client_type, ensure):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(201, json=_agent_body())

    async with _sdk(client_type, handler, operator_api_key="operator-test-key") as client:
        method = client.ensure_agent_registered if ensure else client.register_agent
        agent = await _resolve(method(_registration()))

    assert agent.agent_id == "support-bot"
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/acr/agents"
    assert requests[0].headers["X-Operator-API-Key"] == "operator-test-key"
    assert "Authorization" not in requests[0].headers
    payload = json.loads(requests[0].content)
    assert payload["allowed_tools"] == ["create_ticket"]
    assert "parent_agent_id" not in payload


async def test_ensure_registration_fetches_only_after_conflict(client_type):
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        assert request.headers["X-Operator-API-Key"] == "operator-test-key"
        if request.method == "POST":
            return httpx.Response(409, json={"detail": "already registered"})
        return httpx.Response(200, json=_agent_body())

    async with _sdk(client_type, handler, operator_api_key="operator-test-key") as client:
        agent = await _resolve(client.ensure_agent_registered(_registration()))

    assert agent.agent_id == "support-bot"
    assert calls == [("POST", "/acr/agents"), ("GET", "/acr/agents/support-bot")]


async def test_registration_failure_preserves_error_body_without_fetching(client_type):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(403, json={"detail": "operator role required"})

    async with _sdk(client_type, handler, operator_api_key="wrong-role") as client:
        with pytest.raises(ACRHTTPError, match="operator role required") as caught:
            await _resolve(client.ensure_agent_registered(_registration()))

    assert caught.value.status_code == 403
    assert caught.value.body == {"detail": "operator role required"}
    assert len(requests) == 1


async def test_operator_endpoints_require_key_before_network_io(client_type):
    def handler(request):
        pytest.fail("Missing operator credentials must not make a network request")

    async with _sdk(client_type, handler) as client:
        with pytest.raises(ValueError, match="operator_api_key is required"):
            await _resolve(client.get_agent("support-bot"))


async def test_session_refresh_changes_bearer_token_and_preserves_action_payload(client_type):
    issued = 0
    evaluations = []

    def handler(request):
        nonlocal issued
        if request.url.path == "/acr/agents/support-bot/token":
            assert request.method == "POST"
            assert request.headers["X-Operator-API-Key"] == "operator-test-key"
            issued += 1
            return httpx.Response(
                200,
                json={
                    "agent_id": "support-bot",
                    "access_token": f"token-{issued}",
                    "expires_in_seconds": 300,
                },
            )
        assert request.url.path == "/acr/evaluate"
        assert "X-Operator-API-Key" not in request.headers
        evaluations.append(request)
        return httpx.Response(200, json={"decision": "allow", "correlation_id": "corr-sdk"})

    async with _sdk(client_type, handler, operator_api_key="operator-test-key") as client:
        session = await _resolve(client.issue_agent_session("support-bot"))
        decision = await _resolve(
            session.evaluate(
                EvaluateRequest(
                    agent_id="support-bot", action=ActionRequest(tool_name="create_ticket")
                )
            )
        )
        refreshed = await _resolve(session.refresh_token())
        result = await _resolve(
            session.evaluate_action(
                tool_name="create_ticket",
                parameters={"subject": "Help"},
                description="Open a ticket",
                context={"channel": "support"},
                intent={"goal": "Resolve question"},
            )
        )
        with pytest.raises(ValueError, match="does not match"):
            await _resolve(
                session.evaluate(
                    EvaluateRequest(
                        agent_id="another-agent", action=ActionRequest(tool_name="create_ticket")
                    )
                )
            )

    assert decision.decision == result.decision == "allow"
    assert refreshed.access_token == session.access_token == "token-2"
    assert issued == 2
    assert len(evaluations) == 2
    assert evaluations[0].headers["Authorization"] == "Bearer token-1"
    assert evaluations[1].headers["Authorization"] == "Bearer token-2"
    assert json.loads(evaluations[1].content) == {
        "agent_id": "support-bot",
        "action": {
            "tool_name": "create_ticket",
            "parameters": {"subject": "Help"},
            "description": "Open a ticket",
        },
        "context": {"channel": "support"},
        "intent": {"goal": "Resolve question", "expected_effects": [], "metadata": {}},
    }


@pytest.mark.parametrize(
    "status,decision",
    [(200, "allow"), (202, "escalate"), (403, "deny"), (500, "deny"), (503, "deny")],
)
async def test_evaluate_keeps_normal_governance_decisions_for_supported_statuses(
    client_type, status, decision
):
    async with _sdk(
        client_type,
        lambda request: httpx.Response(
            status, json={"decision": decision, "reason": "policy result"}
        ),
    ) as client:
        response = await _resolve(
            client.evaluate_action(
                agent_id="support-bot", access_token="token", tool_name="create_ticket"
            )
        )
    assert response.decision == decision
    assert response.reason == "policy result"


@pytest.mark.parametrize(
    "status,body,message",
    [
        (401, {"detail": "expired token"}, "Unexpected evaluate response status"),
        (200, "upstream proxy error", "Evaluate response body was not JSON"),
        (503, ["unavailable"], "Evaluate response body was not JSON"),
    ],
)
async def test_evaluate_rejects_transport_errors_and_malformed_bodies(
    client_type, status, body, message
):
    def handler(request):
        return (
            httpx.Response(status, text=body)
            if isinstance(body, str)
            else httpx.Response(status, json=body)
        )

    async with _sdk(client_type, handler) as client:
        with pytest.raises(ACRHTTPError, match=message) as caught:
            await _resolve(
                client.evaluate_action(
                    agent_id="support-bot", access_token="token", tool_name="create_ticket"
                )
            )
    assert caught.value.status_code == status
    assert caught.value.body == body


@pytest.mark.parametrize(
    "endpoint,status,body,message",
    [
        ("health", 200, {"status": "healthy"}, None),
        ("ready", 200, {"ready": True}, None),
        ("ready", 503, {"ready": False, "database": "unavailable"}, None),
        ("health", 502, {"message": "bad gateway"}, "bad gateway"),
        ("ready", 401, {"reason": "unauthorized"}, "unauthorized"),
        ("health", 200, "not json", "Health response body was not JSON"),
        ("ready", 503, "not json", "Ready response body was not JSON"),
        ("health", 500, "proxy failed", "ACR API request failed with status 500"),
    ],
)
async def test_health_readiness_distinguish_unready_from_protocol_errors(
    client_type, endpoint, status, body, message
):
    def handler(request):
        assert request.url.path == f"/acr/{endpoint}"
        assert "Authorization" not in request.headers
        assert "X-Operator-API-Key" not in request.headers
        return (
            httpx.Response(status, text=body)
            if isinstance(body, str)
            else httpx.Response(status, json=body)
        )

    async with _sdk(client_type, handler) as client:
        method = getattr(client, f"get_{endpoint}")
        if message:
            with pytest.raises(ACRHTTPError, match=message) as caught:
                await _resolve(method())
            assert caught.value.status_code == status
            assert caught.value.body == body
        else:
            assert await _resolve(method()) == body


async def test_context_closes_owned_http_client(client_type):
    async with _sdk(
        client_type, lambda request: httpx.Response(200, json={"status": "ok"})
    ) as client:
        assert client.base_url == "https://control.example"
        assert not client._client.is_closed
    assert client._client.is_closed


async def test_context_leaves_injected_http_client_open(client_type):
    http_client_type = httpx.AsyncClient if client_type is AsyncACRClient else httpx.Client
    external = http_client_type(
        base_url="https://control.example",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"status": "ok"})),
    )
    try:
        async with _sdk(
            client_type,
            lambda request: pytest.fail("Injected client must be used"),
            client=external,
        ) as sdk:
            assert await _resolve(sdk.get_health()) == {"status": "ok"}
        assert not external.is_closed
    finally:
        await _resolve(
            external.aclose() if isinstance(external, httpx.AsyncClient) else external.close()
        )
