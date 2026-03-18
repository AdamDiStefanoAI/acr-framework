"""Add policy releases table

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_releases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("release_id", sa.String(64), nullable=False, unique=True),
        sa.Column("draft_id", sa.String(64), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("manifest", JSONB, nullable=False, server_default="{}"),
        sa.Column("rego_policy", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="published"),
        sa.Column("published_by", sa.String(256), nullable=True),
        sa.Column("rollback_from_release_id", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_policy_releases_release_id", "policy_releases", ["release_id"])
    op.create_index("ix_policy_releases_draft_id", "policy_releases", ["draft_id"])
    op.create_index("ix_policy_releases_agent_id", "policy_releases", ["agent_id"])
    op.create_index("ix_policy_releases_status", "policy_releases", ["status"])
    op.create_check_constraint(
        "ck_policy_releases_status",
        "policy_releases",
        "status IN ('published', 'superseded', 'rolled_back')",
    )


def downgrade() -> None:
    op.drop_table("policy_releases")
