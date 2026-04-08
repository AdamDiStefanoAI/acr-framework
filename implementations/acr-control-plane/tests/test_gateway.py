"""Gateway end-to-end tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager

from httpx import AsyncClient


class TestGatewayEvaluate:
    async def test_allow_registered_agent(self, async_client: AsyncClient, sample_agent) -> None:
        resp = await async_client.post(
            "/acr/evaluate",
            json={
                "agent_id": sample_agent.agent_id,
                "action": {"tool_name": "query_customer_db", "parameters": {"customer_id": "C-001"}},
                "context": {"session_id": "sess-abc", "actions_this_minute": 1, "hourly_spend_usd": 0.10},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "allow"
        assert "correlation_id" in data

    async def test_allow_registered_agent_with_intent_metadata(self, async_client: AsyncClient, sample_agent) -> None:
        resp = await async_client.post(
            "/acr/evaluate",
            json={
                "agent_id": sample_agent.agent_id,
                "action": {"tool_name": "query_customer_db", "parameters": {"customer_id": "C-001"}},
                "context": {"session_id": "sess-abc"},
                "intent": {
                    "goal": "Retrieve customer details for a support case",
                    "justification": "Agent needs account context before responding",
                    "requested_by_step": "lookup_customer_record",
                    "expected_effects": ["read customer record"],
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "allow"

    async def test_deny_unregistered_agent(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/acr/evaluate",
            json={
                "agent_id": "unknown-agent-xyz",
                "action": {"tool_name": "query_customer_db", "parameters": {}},
                "context": {},
            },
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["decision"] == "deny"

    async def test_deny_killed_agent(self, async_client: AsyncClient, sample_agent) -> None:
        with patch("acr.gateway.router.is_agent_killed", new_callable=AsyncMock, return_value=True):
            resp = await async_client.post(
                "/acr/evaluate",
                json={
                    "agent_id": sample_agent.agent_id,
                    "action": {"tool_name": "query_customer_db", "parameters": {}},
                    "context": {},
                },
            )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "AGENT_KILLED"

    async def test_killswitch_unavailable_fails_secure(self, async_client: AsyncClient, sample_agent) -> None:
        from acr.common.errors import KillSwitchError

        with patch(
            "acr.gateway.router.is_agent_killed",
            new_callable=AsyncMock,
            side_effect=KillSwitchError("Kill switch state unavailable"),
        ):
            resp = await async_client.post(
                "/acr/evaluate",
                json={
                    "agent_id": sample_agent.agent_id,
                    "action": {"tool_name": "query_customer_db", "parameters": {}},
                    "context": {},
                },
            )

        assert resp.status_code == 503
        assert resp.json()["decision"] == "deny"
        assert resp.json()["error_code"] == "KILLSWITCH_ERROR"

    async def test_escalate_decision(self, async_client: AsyncClient, sample_agent) -> None:
        from acr.pillar2_policy.models import PolicyDecision, PolicyEvaluationResult

        escalate_result = PolicyEvaluationResult(
            final_decision="escalate",
            decisions=[PolicyDecision(policy_id="acr-escalate", decision="escalate", reason="Needs approval")],
            reason="Refund >$100 requires human approval",
            approval_queue="finance-approvals",
            sla_minutes=240,
            latency_ms=10,
        )
        with patch("acr.gateway.router.evaluate_policy", new_callable=AsyncMock, return_value=escalate_result):
            resp = await async_client.post(
                "/acr/evaluate",
                json={
                    "agent_id": sample_agent.agent_id,
                    "action": {"tool_name": "issue_refund", "parameters": {"amount": 250}},
                    "context": {},
                },
            )
        assert resp.status_code == 202
        data = resp.json()
        assert data["decision"] == "escalate"
        assert "approval_request_id" in data

        approval_resp = await async_client.get(f"/acr/approvals/{data['approval_request_id']}")
        assert approval_resp.status_code == 200
        assert approval_resp.json()["status"] == "pending"

    async def test_allow_executes_downstream_when_enabled(self, async_client: AsyncClient, sample_agent) -> None:
        with (
            patch.object(__import__("acr.gateway.router", fromlist=["settings"]).settings, "execute_allowed_actions", True),
            patch(
                "acr.gateway.router.execute_action",
                new_callable=AsyncMock,
                return_value={"status": "executed", "executor": "internal-api"},
            ),
        ):
            resp = await async_client.post(
                "/acr/evaluate",
                json={
                    "agent_id": sample_agent.agent_id,
                    "action": {"tool_name": "query_customer_db", "parameters": {"customer_id": "C-001"}},
                    "context": {},
                },
            )

        assert resp.status_code == 200
        assert resp.json()["execution_result"]["status"] == "executed"

    async def test_policy_engine_down_fails_secure(self, async_client: AsyncClient, sample_agent) -> None:
        from acr.common.errors import PolicyEngineError

        with patch(
            "acr.gateway.router.evaluate_policy",
            new_callable=AsyncMock,
            side_effect=PolicyEngineError("OPA unreachable"),
        ):
            resp = await async_client.post(
                "/acr/evaluate",
                json={
                    "agent_id": sample_agent.agent_id,
                    "action": {"tool_name": "query_customer_db", "parameters": {}},
                    "context": {},
                },
            )
        # Fail-secure: deny when policy engine is unavailable
        assert resp.status_code == 503
        assert resp.json()["decision"] == "deny"

    async def test_correlation_id_propagated(self, async_client: AsyncClient, sample_agent) -> None:
        resp = await async_client.post(
            "/acr/evaluate",
            headers={"X-Correlation-ID": "my-trace-id"},
            json={
                "agent_id": sample_agent.agent_id,
                "action": {"tool_name": "query_customer_db", "parameters": {}},
                "context": {},
            },
        )
        assert resp.headers.get("X-Correlation-ID") == "my-trace-id"


class TestHealthEndpoint:
    async def test_health_returns_ok(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/acr/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    async def test_ready_redacts_dependency_errors(self, async_client: AsyncClient) -> None:
        class _FakeConnection:
            async def execute(self, query) -> None:
                return None

        class _FakeEngine:
            @asynccontextmanager
            async def connect(self):
                yield _FakeConnection()

        class _FakeRedis:
            async def ping(self) -> None:
                raise RuntimeError("Error 61 connecting to localhost:6399")

        class _FailingAsyncClient:
            def __init__(self, *args, **kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

            async def get(self, path: str):
                raise RuntimeError("All connection attempts failed for http://127.0.0.1:8189")

        with (
            patch("acr.main.engine", _FakeEngine()),
            patch("acr.common.redis_client.get_redis", return_value=_FakeRedis()),
            patch("acr.main.httpx.AsyncClient", _FailingAsyncClient),
        ):
            resp = await async_client.get("/acr/ready")

        assert resp.status_code == 503
        assert resp.json() == {
            "status": "not_ready",
            "checks": {"database": "ok", "redis": "error", "opa": "error"},
        }

    async def test_openapi_marks_operator_routes_as_protected(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/openapi.json")
        assert resp.status_code == 200

        spec = resp.json()
        security = spec["paths"]["/acr/agents"]["get"]["security"]
        assert {"HTTPBearer": []} in security
        assert {"APIKeyHeader": []} in security
        assert {"APIKeyCookie": []} in security

    async def test_console_route_serves_html(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/console")
        assert resp.status_code == 200
        assert "Operator Console" in resp.text
        assert "Guided Policy Setup" in resp.text
        assert "Saved Policy Drafts" in resp.text
        assert "Release History" in resp.text

    async def test_console_assets_served(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/console-assets/app.js")
        assert resp.status_code == 200
        assert "refreshDashboard" in resp.text


class TestAgentRegistryAPI:
    async def test_register_and_get(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/acr/agents",
            json={
                "agent_id": "api-test-agent",
                "owner": "test@example.com",
                "purpose": "API testing",
                "allowed_tools": ["tool_x"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == "api-test-agent"

        get_resp = await async_client.get("/acr/agents/api-test-agent")
        assert get_resp.status_code == 200
        assert get_resp.json()["owner"] == "test@example.com"

    async def test_token_issuance(self, async_client: AsyncClient, sample_agent) -> None:
        resp = await async_client.post(f"/acr/agents/{sample_agent.agent_id}/token")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["agent_id"] == sample_agent.agent_id

    async def test_register_duplicate_returns_conflict(self, async_client: AsyncClient) -> None:
        payload = {
            "agent_id": "api-test-agent-duplicate",
            "owner": "test@example.com",
            "purpose": "API testing",
            "allowed_tools": ["tool_x"],
        }

        first = await async_client.post("/acr/agents", json=payload)
        second = await async_client.post("/acr/agents", json=payload)

        assert first.status_code == 201
        assert second.status_code == 409
        assert second.json()["error_code"] == "AGENT_ALREADY_EXISTS"

    async def test_deregistered_agent_cannot_issue_token(self, async_client: AsyncClient, sample_agent) -> None:
        delete_resp = await async_client.delete(f"/acr/agents/{sample_agent.agent_id}")
        assert delete_resp.status_code == 204

        token_resp = await async_client.post(f"/acr/agents/{sample_agent.agent_id}/token")
        assert token_resp.status_code == 403
        assert token_resp.json()["error_code"] == "AGENT_NOT_REGISTERED"


class TestContainmentAPI:
    async def test_list_containment_status(self, async_client: AsyncClient) -> None:
        with patch(
            "acr.pillar5_containment.router.list_kill_status",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await async_client.get("/acr/containment/status")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_kill_agent_via_containment_api(self, async_client: AsyncClient) -> None:
        with patch(
            "acr.pillar5_containment.router.kill_agent",
            new_callable=AsyncMock,
            return_value={
                "agent_id": "agent-1",
                "is_killed": True,
                "reason": "manual shutdown",
                "killed_at": "2026-03-17T10:00:00Z",
                "killed_by": "test-operator",
            },
        ):
            resp = await async_client.post(
                "/acr/containment/kill",
                json={"agent_id": "agent-1", "reason": "manual shutdown"},
            )
        assert resp.status_code == 200
        assert resp.json()["is_killed"] is True
