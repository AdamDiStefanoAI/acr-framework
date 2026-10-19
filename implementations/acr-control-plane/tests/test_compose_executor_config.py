"""Source configuration regression; does not claim a Docker execution pass."""

from pathlib import Path

import yaml


def test_compose_forwards_both_execution_secrets_to_gateway():
    root = Path(__file__).resolve().parents[1]
    document = yaml.safe_load((root / "docker-compose.yml").read_text())
    environment = document["services"]["acr-gateway"]["environment"]
    assert environment["EXECUTOR_HMAC_SECRET"] == "${EXECUTOR_HMAC_SECRET:-}"
    assert environment["EXECUTOR_CREDENTIAL_SECRET"] == "${EXECUTOR_CREDENTIAL_SECRET:-}"


def test_compose_forwards_same_killswitch_secret_to_gateway_and_service():
    root = Path(__file__).resolve().parents[1]
    document = yaml.safe_load((root / "docker-compose.yml").read_text())
    services = document["services"]
    assert (
        services["acr-gateway"]["environment"]["KILLSWITCH_SECRET"]
        == services["acr-killswitch"]["environment"]["KILLSWITCH_SECRET"]
    )


def test_opa_healthcheck_uses_available_binary_and_requires_http_success():
    root = Path(__file__).resolve().parents[1]
    document = yaml.safe_load((root / "docker-compose.yml").read_text())
    probe = document["services"]["opa"]["healthcheck"]["test"]
    assert probe[:4] == ["CMD", "/opa", "eval", "--fail"]
    assert '"url": "http://127.0.0.1:8181/health"' in probe[4]
    assert '"timeout": "2s"' in probe[4]
    assert probe[4].endswith(".status_code == 200")
