"""Add operator credentials table

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operator_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("key_id", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("subject", sa.String(256), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("roles", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.Column("revoked_by", sa.String(256), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_operator_credentials_key_id", "operator_credentials", ["key_id"])
    op.create_index("ix_operator_credentials_key_hash", "operator_credentials", ["key_hash"])
    op.create_index("ix_operator_credentials_is_active", "operator_credentials", ["is_active"])


def downgrade() -> None:
    op.drop_table("operator_credentials")
