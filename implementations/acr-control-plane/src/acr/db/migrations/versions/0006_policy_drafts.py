"""Add policy drafts table

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("draft_id", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("manifest", JSONB, nullable=False, server_default="{}"),
        sa.Column("rego_policy", sa.Text(), nullable=False),
        sa.Column("wizard_inputs", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.Column("updated_by", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_policy_drafts_draft_id", "policy_drafts", ["draft_id"])
    op.create_index("ix_policy_drafts_agent_id", "policy_drafts", ["agent_id"])


def downgrade() -> None:
    op.drop_table("policy_drafts")
