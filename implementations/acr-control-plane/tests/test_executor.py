from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from acr.common.errors import ACRError
from acr.config import assert_production_secrets, settings, tool_executor_map
from acr.gateway.executor import execute_action
from acr.gateway.executor_auth import (
    BrokeredExecutionCredential,
    ExecutionAuthorization,
    require_brokered_execution_credential,
    require_gateway_execution,
)


class _ResponseStub:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _ClientStub:
    def __init__(self, captured: list[dict]) -> None:
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url: str, json: dict, headers: dict) -> _ResponseStub:
        self._captured.append({"url": url, "json": json, "headers": headers})
        return _ResponseStub({"status": "ok", "provider": "stub"})


@pytest.mark.asyncio
async def test_refund_executor_integration_payload(monkeypatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(
        settings,
        "executor_integrations_json",
        '{"issue_refund":{"provider":"refund_api","url":"https://refunds.internal/execute","api_key":"secret","default_currency":"USD"}}',
    )
    from acr.config import executor_integrations

    executor_integrations.cache_clear()
    with patch("acr.gateway.executor_integrations.httpx.AsyncClient", return_value=_ClientStub(captured)):
        result = await execute_action(
            agent_id="agent-1",
            tool_name="issue_refund",
            parameters={"customer_id": "cust-1", "order_id": "ord-1", "amount": 125},
            description="Customer refund",
            correlation_id="corr-1",
        )

    assert result["provider"] == "refund_api"
    assert captured[0]["url"] == "https://refunds.internal/execute"
    assert captured[0]["json"]["refund_request"]["currency"] == "USD"
    assert captured[0]["json"]["refund_request"]["amount"] == 125
    assert captured[0]["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_email_executor_integration_payload(monkeypatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(
        settings,
        "executor_integrations_json",
        '{"send_email":{"provider":"email_api","url":"https://email.internal/send","api_key":"mail-secret","from_address":"ops@example.com"}}',
    )
    from acr.config import executor_integrations

    executor_integrations.cache_clear()
    with patch("acr.gateway.executor_integrations.httpx.AsyncClient", return_value=_ClientStub(captured)):
        result = await execute_action(
            agent_id="agent-2",
            tool_name="send_email",
            parameters={"to": ["user@example.com"], "subject": "Hello", "body": "Body"},
            description=None,
            correlation_id="corr-2",
        )

    assert result["provider"] == "email_api"
    assert captured[0]["json"]["message"]["from"] == "ops@example.com"
    assert captured[0]["json"]["message"]["subject"] == "Hello"


@pytest.mark.asyncio
async def test_generic_executor_includes_short_lived_gateway_proof(monkeypatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(settings, "tool_executor_map_json", '{"query_customer_db":"https://executor.internal/run"}')
    monkeypatch.setattr(settings, "executor_hmac_secret", "x" * 64)
    monkeypatch.setattr(settings, "executor_credential_secret", "c" * 64)
    monkeypatch.setattr(settings, "executor_auth_ttl_seconds", 120)
    tool_executor_map.cache_clear()

    with patch("acr.gateway.executor.httpx.AsyncClient", return_value=_ClientStub(captured)):
        await execute_action(
            agent_id="agent-1",
            tool_name="query_customer_db",
            parameters={"customer_id": "C-001"},
            description="Fetch customer",
            correlation_id="corr-123",
        )

    headers = captured[0]["headers"]
    assert "X-ACR-Execution-Signature" in headers
    assert "X-ACR-Execution-Token" in headers
    assert "X-ACR-Brokered-Credential" in headers
    assert headers["X-ACR-Credential-Audience"] == "tool:query_customer_db"


@pytest.mark.asyncio
async def test_downstream_executor_can_verify_gateway_execution_token(monkeypatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(settings, "tool_executor_map_json", '{"query_customer_db":"https://executor.internal/run"}')
    monkeypatch.setattr(settings, "executor_hmac_secret", "y" * 64)
    monkeypatch.setattr(settings, "executor_credential_secret", "b" * 64)
    tool_executor_map.cache_clear()

    with patch("acr.gateway.executor.httpx.AsyncClient", return_value=_ClientStub(captured)):
        await execute_action(
            agent_id="agent-1",
            tool_name="query_customer_db",
            parameters={"customer_id": "C-001"},
            description="Fetch customer",
            correlation_id="corr-123",
        )

    app = FastAPI()

    @app.exception_handler(ACRError)
    async def acr_error_handler(request, exc: ACRError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message},
        )

    @app.post("/execute")
    async def execute_endpoint(
        auth: ExecutionAuthorization = Depends(require_gateway_execution),
        brokered: BrokeredExecutionCredential = Depends(require_brokered_execution_credential),
    ) -> dict:
        return {
            "agent_id": auth.agent_id,
            "tool_name": auth.tool_name,
            "correlation_id": auth.correlation_id,
            "audience": brokered.audience,
            "scopes": list(brokered.scopes),
        }

    request_body = captured[0]["json"]
    request_headers = {
        "X-ACR-Execution-Token": captured[0]["headers"]["X-ACR-Execution-Token"],
        "X-ACR-Brokered-Credential": captured[0]["headers"]["X-ACR-Brokered-Credential"],
        "X-ACR-Credential-Audience": captured[0]["headers"]["X-ACR-Credential-Audience"],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        valid = await client.post("/execute", json=request_body, headers=request_headers)
        tampered = await client.post(
            "/execute",
            json={**request_body, "parameters": {"customer_id": "C-999"}},
            headers=request_headers,
        )
        wrong_audience = await client.post(
            "/execute",
            json=request_body,
            headers={**request_headers, "X-ACR-Credential-Audience": "tool:other"},
        )

    assert valid.status_code == 200
    assert valid.json()["tool_name"] == "query_customer_db"
    assert valid.json()["audience"] == "tool:query_customer_db"
    assert valid.json()["scopes"] == ["tool:query_customer_db:execute"]
    assert tampered.status_code == 401
    assert tampered.json()["error_code"] == "INVALID_EXECUTION_AUTHORIZATION"
    assert wrong_audience.status_code == 401
    assert wrong_audience.json()["error_code"] == "INVALID_EXECUTION_AUTHORIZATION"


def test_production_requires_executor_secret_for_live_execution(monkeypatch) -> None:
    monkeypatch.setattr(settings, "acr_env", "production")
    monkeypatch.setattr(settings, "execute_allowed_actions", True)
    monkeypatch.setattr(settings, "executor_hmac_secret", "")
    monkeypatch.setattr(settings, "jwt_secret_key", "z" * 64)
    monkeypatch.setattr(settings, "killswitch_secret", "k" * 64)
    monkeypatch.setattr(settings, "operator_api_keys_json", '{"bootstrap":{"subject":"ops","roles":["security_admin"]}}')
    monkeypatch.setattr(settings, "oidc_enabled", False)

    with pytest.raises(RuntimeError, match="EXECUTOR_HMAC_SECRET"):
        assert_production_secrets()


def test_production_requires_strong_executor_credential_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "acr_env", "production")
    monkeypatch.setattr(settings, "execute_allowed_actions", False)
    monkeypatch.setattr(settings, "executor_credential_secret", "short")
    monkeypatch.setattr(settings, "jwt_secret_key", "z" * 64)
    monkeypatch.setattr(settings, "killswitch_secret", "k" * 64)
    monkeypatch.setattr(settings, "operator_api_keys_json", '{"bootstrap":{"subject":"ops","roles":["security_admin"]}}')
    monkeypatch.setattr(settings, "oidc_enabled", False)

    with pytest.raises(RuntimeError, match="EXECUTOR_CREDENTIAL_SECRET"):
        assert_production_secrets()
