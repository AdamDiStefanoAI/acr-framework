"""Add governed drift baseline versions

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drift_baseline_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("baseline_version_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("baseline_data", sa.JSON(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("approved_by", sa.String(length=256), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(length=256), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(length=256), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('candidate', 'approved', 'active', 'rejected', 'superseded')",
            name="ck_drift_baseline_versions_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_drift_baseline_versions_agent_status",
        "drift_baseline_versions",
        ["agent_id", "status"],
    )
    op.create_index(
        "ix_drift_baseline_versions_agent_id",
        "drift_baseline_versions",
        ["agent_id"],
    )
    op.create_index(
        "ix_drift_baseline_versions_baseline_version_id",
        "drift_baseline_versions",
        ["baseline_version_id"],
        unique=True,
    )
    op.create_index(
        "ix_drift_baseline_versions_created_at",
        "drift_baseline_versions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_drift_baseline_versions_created_at", table_name="drift_baseline_versions")
    op.drop_index("ix_drift_baseline_versions_baseline_version_id", table_name="drift_baseline_versions")
    op.drop_index("ix_drift_baseline_versions_agent_id", table_name="drift_baseline_versions")
    op.drop_index("ix_drift_baseline_versions_agent_status", table_name="drift_baseline_versions")
    op.drop_table("drift_baseline_versions")
