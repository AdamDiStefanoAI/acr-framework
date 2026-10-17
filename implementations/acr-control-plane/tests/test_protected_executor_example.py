"""Smoke checks for the runnable, least-privilege executor example."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from acr.common.errors import InvalidExecutionAuthorizationError
from examples.protected_executor import app as executor_example
from examples.protected_executor.app import app


def test_executor_container_sets_unprivileged_runtime_user() -> None:
    dockerfile = Path(__file__).resolve().parents[1] / "examples/protected_executor/Dockerfile"
    instructions = [line.strip() for line in dockerfile.read_text().splitlines()]
    users = [line.split(maxsplit=1)[1] for line in instructions if line.startswith("USER ")]
    assert users and users[-1] not in {"root", "0", "root:root", "0:0"}
    ports = [line.split(maxsplit=1)[1] for line in instructions if line.startswith("EXPOSE ")]
    assert ports and all(int(port) >= 1024 for port in ports)


def test_executor_health_and_metadata_without_external_services(monkeypatch) -> None:
    monkeypatch.delenv("PROTECTED_EXECUTOR_ALLOWED_TOOLS", raising=False)
    with TestClient(app) as client:
        health = client.get("/health")
        metadata = client.get("/metadata")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert metadata.status_code == 200
    assert metadata.json() == {
        "executor": "acr-protected-executor",
        "exposed_tools": ["create_ticket", "issue_refund", "query_customer_db", "send_email"],
        "requires_gateway_execution_token": True,
        "requires_brokered_credential": True,
    }


def test_executor_exposes_only_configured_tools(monkeypatch) -> None:
    monkeypatch.setenv("PROTECTED_EXECUTOR_ALLOWED_TOOLS", "query_customer_db, unknown_tool")
    with TestClient(app) as client:
        metadata = client.get("/metadata")

    assert metadata.json()["exposed_tools"] == ["query_customer_db"]


def test_executor_denies_execution_without_gateway_credentials(monkeypatch) -> None:
    tool = Mock()
    monkeypatch.setitem(executor_example._ALLOWED_TOOLS, "query_customer_db", tool)
    with (
        TestClient(app) as client,
        pytest.raises(
            InvalidExecutionAuthorizationError, match="X-ACR-Execution-Token header is required"
        ),
    ):
        client.post(
            "/execute",
            json={"tool_name": "query_customer_db", "parameters": {"customer_id": "C-12345"}},
        )

    tool.assert_not_called()
