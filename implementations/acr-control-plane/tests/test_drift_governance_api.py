from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from acr.db.models import DriftMetricRecord


async def _seed_samples(db: AsyncSession, agent_id: str, n: int = 40) -> None:
    tools = ["tool_a", "tool_b", "tool_c"]
    for i in range(n):
        db.add(
            DriftMetricRecord(
                agent_id=agent_id,
                correlation_id=f"corr-{agent_id}-{i}",
                tool_name=tools[i % len(tools)],
                action_type="action",
                policy_denied=False,
                latency_ms=25 + i,
            )
        )
    await db.commit()


class TestDriftGovernanceAPI:
    async def test_governed_baseline_actions_emit_audit_events(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        sample_agent,
    ) -> None:
        await _seed_samples(db, sample_agent.agent_id)

        propose_resp = await async_client.post(
            f"/acr/drift/{sample_agent.agent_id}/baseline/propose",
            json={"window_days": 30, "notes": "Propose a fresh baseline"},
        )
        assert propose_resp.status_code == 200
        baseline_version_id = propose_resp.json()["baseline_version_id"]

        approve_resp = await async_client.post(
            f"/acr/drift/{sample_agent.agent_id}/baseline/{baseline_version_id}/approve",
            json={"notes": "Approved after review"},
        )
        assert approve_resp.status_code == 200

        activate_resp = await async_client.post(
            f"/acr/drift/{sample_agent.agent_id}/baseline/{baseline_version_id}/activate",
            json={"notes": "Activate the new normal"},
        )
        assert activate_resp.status_code == 200

        events_resp = await async_client.get(
            "/acr/events",
            params={"agent_id": sample_agent.agent_id, "event_type": "human_intervention", "limit": 10},
        )
        assert events_resp.status_code == 200
        events = events_resp.json()
        actions = {event["custom"].get("baseline_action") for event in events}
        assert {"proposed", "approved", "activated"} <= actions

        governed_events = [event for event in events if event["request"]["tool_name"] == "baseline_governance"]
        assert governed_events
        assert any(
            event["custom"].get("baseline_version_id") == baseline_version_id
            for event in governed_events
        )

    async def test_reset_baseline_emits_human_intervention_event(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        sample_agent,
    ) -> None:
        await _seed_samples(db, sample_agent.agent_id)

        response = await async_client.post(
            f"/acr/drift/{sample_agent.agent_id}/baseline/reset",
        )
        assert response.status_code == 200

        events_resp = await async_client.get(
            "/acr/events",
            params={"agent_id": sample_agent.agent_id, "event_type": "human_intervention", "limit": 10},
        )
        assert events_resp.status_code == 200
        assert any(
            event["custom"].get("baseline_action") == "reset"
            for event in events_resp.json()
        )
