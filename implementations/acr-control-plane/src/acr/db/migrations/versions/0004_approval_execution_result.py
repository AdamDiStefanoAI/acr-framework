"""Add execution_result to approval requests

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "approval_requests",
        sa.Column("execution_result", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("approval_requests", "execution_result")
