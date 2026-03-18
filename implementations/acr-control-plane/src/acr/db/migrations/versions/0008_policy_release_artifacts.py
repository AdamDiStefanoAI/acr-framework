"""Add artifact metadata to policy releases

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("policy_releases", sa.Column("artifact_uri", sa.String(length=1024), nullable=True))
    op.add_column("policy_releases", sa.Column("artifact_sha256", sa.String(length=64), nullable=True))
    op.add_column("policy_releases", sa.Column("publish_backend", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("policy_releases", "publish_backend")
    op.drop_column("policy_releases", "artifact_sha256")
    op.drop_column("policy_releases", "artifact_uri")
