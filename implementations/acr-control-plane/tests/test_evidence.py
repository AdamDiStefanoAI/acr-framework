from __future__ import annotations

import io
import json
import zipfile

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from acr.pillar4_observability.schema import LatencyBreakdown
from acr.pillar4_observability.telemetry import build_event, persist_event


class TestEvidenceBundles:
    async def test_export_evidence_bundle_for_correlation_id(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        sample_agent,
    ) -> None:
        correlation_id = "corr-evidence-123"
        event = build_event(
            event_type="ai_inference",
            agent_id=sample_agent.agent_id,
            agent_purpose=sample_agent.purpose,
            agent_capabilities=sample_agent.allowed_tools or [],
            correlation_id=correlation_id,
            session_id="sess-1",
            tool_name="query_customer_db",
            parameters={"customer_id": "C-001"},
            description="Lookup customer",
            context={"session_id": "sess-1"},
            start_time="2026-03-17T00:00:00Z",
            end_time="2026-03-17T00:00:01Z",
            duration_ms=100,
            latency_breakdown=LatencyBreakdown(identity_ms=10, policy_ms=20, total_ms=30),
            policies=[],
            output_decision="allow",
            output_reason=None,
            approval_request_id=None,
            drift_score=0.1,
        )
        await persist_event(db, event)
        await db.commit()

        bundle_response = await async_client.get(f"/acr/evidence/{correlation_id}")
        assert bundle_response.status_code == 200
        assert bundle_response.headers["x-evidence-bundle-sha256"]

        archive_bytes = io.BytesIO(bundle_response.content)
        with zipfile.ZipFile(archive_bytes) as archive:
            names = set(archive.namelist())
            assert {"manifest.json", "events.jsonl", "checksums.sha256"} <= names

            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["correlation_id"] == correlation_id
            assert manifest["agent_id"] == sample_agent.agent_id
            assert manifest["event_count"] >= 1

            events = [
                json.loads(line)
                for line in archive.read("events.jsonl").decode().splitlines()
                if line.strip()
            ]
            assert any(event["request"]["request_id"] == correlation_id for event in events)

            checksums = archive.read("checksums.sha256").decode()
            assert "manifest.json" in checksums
            assert "events.jsonl" in checksums

    async def test_export_evidence_bundle_not_found(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/acr/evidence/corr-does-not-exist")
        assert response.status_code == 404
        assert response.json()["error_code"] == "EVIDENCE_BUNDLE_NOT_FOUND"
