"""Add activation tracking to policy releases

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "policy_releases",
        sa.Column("activation_status", sa.String(length=16), nullable=False, server_default="inactive"),
    )
    op.add_column("policy_releases", sa.Column("active_bundle_uri", sa.String(length=1024), nullable=True))
    op.add_column("policy_releases", sa.Column("activated_by", sa.String(length=256), nullable=True))
    op.add_column("policy_releases", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_policy_releases_activation_status", "policy_releases", ["activation_status"])
    op.alter_column("policy_releases", "activation_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_policy_releases_activation_status", table_name="policy_releases")
    op.drop_column("policy_releases", "activated_at")
    op.drop_column("policy_releases", "activated_by")
    op.drop_column("policy_releases", "active_bundle_uri")
    op.drop_column("policy_releases", "activation_status")
