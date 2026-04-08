"""Agent registry expansion: lineage, capabilities, lifecycle, health

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-07

Adds the columns required for richer agent governance:
  * version            — agent's own semantic version
  * parent_agent_id    — orchestrator/parent for lineage
  * capabilities       — declared skill tags (separate from tool allowlist)
  * lifecycle_state    — draft | active | deprecated | retired
  * health_status      — unknown | healthy | degraded | unhealthy
  * last_heartbeat_at  — wall-clock of last heartbeat

The legacy `is_active` boolean is kept and back-filled to stay in sync with
`lifecycle_state` (False ⇔ retired). Existing rows are migrated to
lifecycle_state='active' / 'retired' based on their current is_active value.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New columns — all nullable=False with server defaults so existing rows
    # back-fill cleanly without a separate UPDATE pass.
    op.add_column(
        "agents",
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0.0"),
    )
    op.add_column(
        "agents",
        sa.Column("parent_agent_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column(
            "capabilities",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "lifecycle_state",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "health_status",
            sa.String(length=16),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "agents",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Back-fill: any pre-existing deregistered agent should be marked retired,
    # not 'active' (which is the column default for new rows).
    op.execute(
        "UPDATE agents SET lifecycle_state = 'retired' WHERE is_active = false"
    )

    # Constraints + indexes.
    op.create_check_constraint(
        "ck_agents_lifecycle_state",
        "agents",
        "lifecycle_state IN ('draft', 'active', 'deprecated', 'retired')",
    )
    op.create_check_constraint(
        "ck_agents_health_status",
        "agents",
        "health_status IN ('unknown', 'healthy', 'degraded', 'unhealthy')",
    )
    op.create_index("ix_agents_parent_agent_id", "agents", ["parent_agent_id"])
    op.create_index("ix_agents_lifecycle_state", "agents", ["lifecycle_state"])


def downgrade() -> None:
    op.drop_index("ix_agents_lifecycle_state", table_name="agents")
    op.drop_index("ix_agents_parent_agent_id", table_name="agents")
    op.drop_constraint("ck_agents_health_status", "agents", type_="check")
    op.drop_constraint("ck_agents_lifecycle_state", "agents", type_="check")
    op.drop_column("agents", "last_heartbeat_at")
    op.drop_column("agents", "health_status")
    op.drop_column("agents", "lifecycle_state")
    op.drop_column("agents", "capabilities")
    op.drop_column("agents", "parent_agent_id")
    op.drop_column("agents", "version")
