"""Pillar 1 unit tests: agent registry and token issuance."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import (
    AgentAlreadyExistsError,
    AgentLifecycleError,
    AgentNotFoundError,
    AgentNotRegisteredError,
)
from acr.pillar1_identity.models import (
    AgentBoundaries,
    AgentRegisterRequest,
    AgentUpdateRequest,
)
from acr.pillar1_identity.registry import (
    deregister_agent,
    discover_agents,
    get_agent,
    get_lineage,
    list_agents,
    record_heartbeat,
    register_agent,
    sweep_stale_heartbeats,
    transition_lifecycle,
    update_agent,
)
from acr.pillar1_identity.validator import decode_token, issue_token, validate_agent_identity


class TestAgentRegistry:
    async def test_register_agent(self, db: AsyncSession) -> None:
        req = AgentRegisterRequest(
            agent_id="test-agent-01",
            owner="team@example.com",
            purpose="testing",
            allowed_tools=["tool_a", "tool_b"],
        )
        record = await register_agent(db, req)
        assert record.agent_id == "test-agent-01"
        assert record.owner == "team@example.com"
        assert record.is_active is True

    async def test_get_agent(self, db: AsyncSession, sample_agent) -> None:
        record = await get_agent(db, sample_agent.agent_id)
        assert record.agent_id == sample_agent.agent_id

    async def test_get_agent_not_found(self, db: AsyncSession) -> None:
        with pytest.raises(AgentNotFoundError):
            await get_agent(db, "nonexistent-agent")

    async def test_list_agents(self, db: AsyncSession, sample_agent) -> None:
        agents = await list_agents(db)
        assert len(agents) >= 1
        ids = [a.agent_id for a in agents]
        assert sample_agent.agent_id in ids

    async def test_update_agent(self, db: AsyncSession, sample_agent) -> None:
        req = AgentUpdateRequest(owner="new-team@example.com")
        updated = await update_agent(db, sample_agent.agent_id, req)
        assert updated.owner == "new-team@example.com"

    async def test_deregister_agent(self, db: AsyncSession, sample_agent) -> None:
        await deregister_agent(db, sample_agent.agent_id)
        record = await get_agent(db, sample_agent.agent_id)
        assert record.is_active is False

    async def test_register_duplicate_agent_raises_conflict(self, db: AsyncSession) -> None:
        req = AgentRegisterRequest(
            agent_id="duplicate-agent",
            owner="team@example.com",
            purpose="testing",
            allowed_tools=["tool_a"],
        )
        await register_agent(db, req)
        await db.commit()

        with pytest.raises(AgentAlreadyExistsError):
            await register_agent(db, req)


class TestTokens:
    def test_issue_and_decode_token(self) -> None:
        token, expires = issue_token("agent-xyz")
        assert expires > 0
        agent_id = decode_token(token)
        assert agent_id == "agent-xyz"

    def test_invalid_token_raises(self) -> None:
        from acr.common.errors import InvalidTokenError
        with pytest.raises(InvalidTokenError):
            decode_token("not.a.valid.jwt")

    async def test_deregistered_agent_cannot_issue_token(self, db: AsyncSession, sample_agent) -> None:
        await deregister_agent(db, sample_agent.agent_id)
        await db.commit()

        with pytest.raises(AgentNotRegisteredError):
            await validate_agent_identity(db, sample_agent.agent_id, check_kill_switch=False)


# ── Registry expansion: lifecycle, heartbeat, lineage, discovery ─────────────


class TestLifecycle:
    async def test_register_defaults_to_active(self, db: AsyncSession, sample_agent) -> None:
        assert sample_agent.lifecycle_state == "active"
        assert sample_agent.is_active is True

    async def test_register_as_draft(self, db: AsyncSession) -> None:
        req = AgentRegisterRequest(
            agent_id="draft-agent",
            owner="team@example.com",
            purpose="staged rollout",
            lifecycle_state="draft",
        )
        record = await register_agent(db, req)
        assert record.lifecycle_state == "draft"
        assert record.is_active is True  # draft is not retired

    async def test_draft_agent_blocked_from_validation(self, db: AsyncSession) -> None:
        req = AgentRegisterRequest(
            agent_id="draft-blocked",
            owner="team@example.com",
            purpose="staged rollout",
            lifecycle_state="draft",
        )
        await register_agent(db, req)
        await db.commit()

        with pytest.raises(AgentLifecycleError):
            await validate_agent_identity(db, "draft-blocked", check_kill_switch=False)

    async def test_lifecycle_transition_draft_to_active(
        self, db: AsyncSession
    ) -> None:
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="promote-me",
                owner="team@example.com",
                purpose="ready to ship",
                lifecycle_state="draft",
            ),
        )
        await db.commit()

        record = await transition_lifecycle(db, "promote-me", "active")
        assert record.lifecycle_state == "active"

        # And now it's allowed to evaluate
        validated = await validate_agent_identity(
            db, "promote-me", check_kill_switch=False
        )
        assert validated.agent_id == "promote-me"

    async def test_illegal_transition_rejected(
        self, db: AsyncSession, sample_agent
    ) -> None:
        # active → draft is not allowed
        with pytest.raises(AgentLifecycleError):
            await transition_lifecycle(db, sample_agent.agent_id, "draft")

    async def test_retired_is_terminal(
        self, db: AsyncSession, sample_agent
    ) -> None:
        await transition_lifecycle(db, sample_agent.agent_id, "retired")
        with pytest.raises(AgentLifecycleError):
            await transition_lifecycle(db, sample_agent.agent_id, "active")

    async def test_deregister_sets_retired_state(
        self, db: AsyncSession, sample_agent
    ) -> None:
        await deregister_agent(db, sample_agent.agent_id)
        record = await get_agent(db, sample_agent.agent_id)
        assert record.lifecycle_state == "retired"
        assert record.is_active is False

    async def test_deprecated_agent_still_evaluates(
        self, db: AsyncSession, sample_agent
    ) -> None:
        await transition_lifecycle(db, sample_agent.agent_id, "deprecated")
        validated = await validate_agent_identity(
            db, sample_agent.agent_id, check_kill_switch=False
        )
        assert validated.lifecycle_state == "deprecated"


class TestHeartbeat:
    async def test_heartbeat_sets_health_and_timestamp(
        self, db: AsyncSession, sample_agent
    ) -> None:
        record = await record_heartbeat(db, sample_agent.agent_id)
        assert record.health_status == "healthy"
        assert record.last_heartbeat_at is not None

    async def test_retired_agent_rejects_heartbeat(
        self, db: AsyncSession, sample_agent
    ) -> None:
        await deregister_agent(db, sample_agent.agent_id)
        with pytest.raises(AgentLifecycleError):
            await record_heartbeat(db, sample_agent.agent_id)

    async def test_sweep_downgrades_stale_agents(
        self, db: AsyncSession, sample_agent
    ) -> None:
        # Mark as healthy with a heartbeat that's already in the past.
        await record_heartbeat(db, sample_agent.agent_id)
        record = await get_agent(db, sample_agent.agent_id)
        record.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=600)
        await db.flush()

        downgraded = await sweep_stale_heartbeats(db, threshold_seconds=60)
        assert downgraded == 1

        record = await get_agent(db, sample_agent.agent_id)
        assert record.health_status == "unhealthy"

    async def test_sweep_ignores_agents_without_heartbeat(
        self, db: AsyncSession, sample_agent
    ) -> None:
        downgraded = await sweep_stale_heartbeats(db, threshold_seconds=60)
        assert downgraded == 0
        # Untouched — still 'unknown'
        record = await get_agent(db, sample_agent.agent_id)
        assert record.health_status == "unknown"


class TestLineage:
    async def test_register_with_parent_attaches_lineage(
        self, db: AsyncSession, sample_agent
    ) -> None:
        child = await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="child-agent-01",
                owner="team@example.com",
                purpose="subagent",
                parent_agent_id=sample_agent.agent_id,
            ),
        )
        assert child.parent_agent_id == sample_agent.agent_id

    async def test_get_lineage_walks_chain(
        self, db: AsyncSession, sample_agent
    ) -> None:
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="mid",
                owner="team@example.com",
                purpose="middle",
                parent_agent_id=sample_agent.agent_id,
            ),
        )
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="leaf",
                owner="team@example.com",
                purpose="leaf",
                parent_agent_id="mid",
            ),
        )
        await db.commit()

        ancestors, children = await get_lineage(db, "leaf")
        ids = [a.agent_id for a in ancestors]
        assert ids == [sample_agent.agent_id, "mid", "leaf"]
        assert children == []

        # The middle node has one child
        _, mid_children = await get_lineage(db, "mid")
        assert [c.agent_id for c in mid_children] == ["leaf"]

    async def test_cannot_attach_to_retired_parent(
        self, db: AsyncSession, sample_agent
    ) -> None:
        await deregister_agent(db, sample_agent.agent_id)
        await db.commit()
        with pytest.raises(AgentLifecycleError):
            await register_agent(
                db,
                AgentRegisterRequest(
                    agent_id="orphaned",
                    owner="team@example.com",
                    purpose="orphan",
                    parent_agent_id=sample_agent.agent_id,
                ),
            )


class TestDiscovery:
    async def test_discover_by_capability(self, db: AsyncSession) -> None:
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="cap-a",
                owner="team@example.com",
                purpose="A",
                capabilities=["billing.refund", "customer.read"],
            ),
        )
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="cap-b",
                owner="team@example.com",
                purpose="B",
                capabilities=["customer.read"],
            ),
        )
        await db.commit()

        found = await discover_agents(db, capability="billing.refund")
        ids = {a.agent_id for a in found}
        assert ids == {"cap-a"}

        found = await discover_agents(db, capability="customer.read")
        ids = {a.agent_id for a in found}
        assert ids == {"cap-a", "cap-b"}

    async def test_discover_excludes_drafts_and_retired_by_default(
        self, db: AsyncSession
    ) -> None:
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="active-one",
                owner="team@example.com",
                purpose="A",
                capabilities=["x"],
            ),
        )
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="draft-one",
                owner="team@example.com",
                purpose="D",
                capabilities=["x"],
                lifecycle_state="draft",
            ),
        )
        await db.commit()

        found = await discover_agents(db, capability="x")
        ids = {a.agent_id for a in found}
        assert ids == {"active-one"}

    async def test_discover_by_parent(
        self, db: AsyncSession, sample_agent
    ) -> None:
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="kid-1",
                owner="team@example.com",
                purpose="k1",
                parent_agent_id=sample_agent.agent_id,
            ),
        )
        await register_agent(
            db,
            AgentRegisterRequest(
                agent_id="kid-2",
                owner="team@example.com",
                purpose="k2",
                parent_agent_id=sample_agent.agent_id,
            ),
        )
        await db.commit()

        found = await discover_agents(db, parent_agent_id=sample_agent.agent_id)
        ids = {a.agent_id for a in found}
        assert ids == {"kid-1", "kid-2"}
