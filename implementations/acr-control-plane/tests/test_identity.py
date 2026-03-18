"""Pillar 1 unit tests: agent registry and token issuance."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import AgentAlreadyExistsError, AgentNotFoundError, AgentNotRegisteredError
from acr.pillar1_identity.models import AgentBoundaries, AgentRegisterRequest, AgentUpdateRequest
from acr.pillar1_identity.registry import (
    deregister_agent,
    get_agent,
    list_agents,
    register_agent,
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
