"""Tests for pillar5_containment/service.py — independent kill switch FastAPI app."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import fakeredis.aioredis

from acr.pillar5_containment import service as ks

SECRET = "test-killswitch-secret-ci"
OPERATOR_KEY = "test-operator-key-ci"


@pytest_asyncio.fixture
async def killswitch_client():
    """Inject fakeredis and a test secret directly into the service module."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    original_redis = ks._redis
    original_secret = ks.KILLSWITCH_SECRET
    original_operator_keys = ks.OPERATOR_API_KEYS_JSON
    ks._redis = fake_redis
    ks.KILLSWITCH_SECRET = SECRET
    ks.OPERATOR_API_KEYS_JSON = (
        '{"test-operator-key-ci":{"subject":"security-team","roles":["security_admin","killswitch_operator","auditor"]}}'
    )

    async with AsyncClient(
        transport=ASGITransport(app=ks.app), base_url="http://test"
    ) as client:
        yield client

    ks._redis = original_redis
    ks.KILLSWITCH_SECRET = original_secret
    ks.OPERATOR_API_KEYS_JSON = original_operator_keys
    await fake_redis.aclose()


# ── Health ────────────────────────────────────────────────────────────────────

class TestKillSwitchHealth:
    async def test_health_returns_ok(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        assert resp.json()["redis"] == "ok"


# ── Kill ──────────────────────────────────────────────────────────────────────

class TestKillEndpoint:
    async def test_kill_agent_success(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-01", "reason": "anomaly detected", "operator_id": "security-team"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_killed"] is True
        assert data["agent_id"] == "bot-01"
        assert data["reason"] == "anomaly detected"
        assert data["killed_at"] is not None

    async def test_kill_requires_secret_header(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-01", "reason": "test"},
        )
        assert resp.status_code == 401

    async def test_kill_wrong_secret_rejected(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-01", "reason": "test"},
            headers={"X-Killswitch-Secret": "completely-wrong", "X-Operator-API-Key": OPERATOR_KEY},
        )
        assert resp.status_code == 401


# ── Restore ───────────────────────────────────────────────────────────────────

class TestRestoreEndpoint:
    async def test_restore_clears_kill_state(self, killswitch_client: AsyncClient):
        # Kill first
        await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-restore", "reason": "test"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        # Restore
        resp = await killswitch_client.post(
            "/acr/kill/restore",
            json={"agent_id": "bot-restore"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        assert resp.status_code == 200
        assert resp.json()["is_killed"] is False

    async def test_restore_requires_secret(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.post(
            "/acr/kill/restore",
            json={"agent_id": "bot-restore"},
        )
        assert resp.status_code == 401


# ── Status ────────────────────────────────────────────────────────────────────

class TestStatusEndpoints:
    async def test_status_not_killed(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.get(
            "/acr/kill/status/never-killed-agent",
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        assert resp.status_code == 200
        assert resp.json()["is_killed"] is False

    async def test_status_killed_agent_shows_metadata(self, killswitch_client: AsyncClient):
        await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-status", "reason": "drift exceeded threshold", "operator_id": "auto"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        resp = await killswitch_client.get(
            "/acr/kill/status/bot-status",
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_killed"] is True
        assert data["reason"] == "drift exceeded threshold"
        assert data["killed_by"] == "auto"

    async def test_status_requires_secret(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.get("/acr/kill/status/bot-01")
        assert resp.status_code == 401

    async def test_list_status_returns_killed_agents(self, killswitch_client: AsyncClient):
        await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-list-1", "reason": "test"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-list-2", "reason": "test"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        resp = await killswitch_client.get(
            "/acr/kill/status",
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = {item["agent_id"] for item in data}
        assert "bot-list-1" in agent_ids
        assert "bot-list-2" in agent_ids

    async def test_list_status_empty_initially(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.get(
            "/acr/kill/status",
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_status_requires_secret(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.get("/acr/kill/status")
        assert resp.status_code == 401

    async def test_killed_then_restored_disappears_from_list(self, killswitch_client: AsyncClient):
        await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-cycle", "reason": "test"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        await killswitch_client.post(
            "/acr/kill/restore",
            json={"agent_id": "bot-cycle"},
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        resp = await killswitch_client.get(
            "/acr/kill/status",
            headers={"X-Killswitch-Secret": SECRET, "X-Operator-API-Key": OPERATOR_KEY},
        )
        agent_ids = {item["agent_id"] for item in resp.json()}
        assert "bot-cycle" not in agent_ids

    async def test_kill_requires_operator_api_key(self, killswitch_client: AsyncClient):
        resp = await killswitch_client.post(
            "/acr/kill",
            json={"agent_id": "bot-02", "reason": "test"},
            headers={"X-Killswitch-Secret": SECRET},
        )
        assert resp.status_code == 401
