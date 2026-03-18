"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agents
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(128), nullable=False, unique=True),
        sa.Column("owner", sa.String(256), nullable=False),
        sa.Column("purpose", sa.String(512), nullable=False),
        sa.Column("risk_tier", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("allowed_tools", JSONB, nullable=False, server_default="[]"),
        sa.Column("forbidden_tools", JSONB, nullable=False, server_default="[]"),
        sa.Column("data_access", JSONB, nullable=False, server_default="[]"),
        sa.Column("boundaries", JSONB, nullable=False, server_default="{}"),
        sa.Column("credential_hash", sa.String(256), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agents_agent_id", "agents", ["agent_id"])

    # policy_decisions
    op.create_table(
        "policy_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("agent_id", sa.String(128), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("policy_id", sa.String(128), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("tool_name", sa.String(128), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_policy_decisions_correlation_id", "policy_decisions", ["correlation_id"])
    op.create_index("ix_policy_decisions_agent_id", "policy_decisions", ["agent_id"])

    # telemetry_events
    op.create_table(
        "telemetry_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_telemetry_events_event_id", "telemetry_events", ["event_id"])
    op.create_index("ix_telemetry_events_correlation_id", "telemetry_events", ["correlation_id"])
    op.create_index("ix_telemetry_events_agent_id", "telemetry_events", ["agent_id"])
    op.create_index("ix_telemetry_events_created_at", "telemetry_events", ["created_at"])

    # approval_requests
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False, unique=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("agent_id", sa.String(128), sa.ForeignKey("agents.agent_id"), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("parameters", JSONB, nullable=False, server_default="{}"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("risk_tier", sa.String(16), nullable=False, server_default="high"),
        sa.Column("approval_queue", sa.String(128), nullable=False, server_default="default"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("decision", sa.String(16), nullable=True),
        sa.Column("decided_by", sa.String(256), nullable=True),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column("sla_minutes", sa.Integer, nullable=False, server_default="240"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_requests_request_id", "approval_requests", ["request_id"])
    op.create_index("ix_approval_requests_agent_id", "approval_requests", ["agent_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])

    # drift_baselines
    op.create_table(
        "drift_baselines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(128), nullable=False, unique=True),
        sa.Column("baseline_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("collection_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_drift_baselines_agent_id", "drift_baselines", ["agent_id"])

    # drift_metrics
    op.create_table(
        "drift_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=True),
        sa.Column("action_type", sa.String(64), nullable=True),
        sa.Column("policy_denied", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_drift_metrics_agent_id", "drift_metrics", ["agent_id"])
    op.create_index("ix_drift_metrics_created_at", "drift_metrics", ["created_at"])

    # containment_actions
    op.create_table(
        "containment_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("tier", sa.Integer, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("drift_score", sa.Float, nullable=True),
        sa.Column("operator_id", sa.String(256), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_containment_actions_agent_id", "containment_actions", ["agent_id"])


def downgrade() -> None:
    op.drop_table("containment_actions")
    op.drop_table("drift_metrics")
    op.drop_table("drift_baselines")
    op.drop_table("approval_requests")
    op.drop_table("telemetry_events")
    op.drop_table("policy_decisions")
    op.drop_table("agents")
