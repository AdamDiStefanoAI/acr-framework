"""Add ON DELETE CASCADE to agent FKs; add composite performance indexes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-16

Changes:
  - policy_decisions.agent_id FK: add ON DELETE CASCADE
  - approval_requests.agent_id FK: add ON DELETE CASCADE
  - approval_requests: add composite index (status, expires_at) for SLA expiry loop
  - approval_requests: add index on correlation_id (present in ORM, missing from 0001)
  - drift_metrics: add composite index (agent_id, created_at) for drift detector queries
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── policy_decisions: drop old FK, re-add with ON DELETE CASCADE ──────────
    op.drop_constraint(
        "policy_decisions_agent_id_fkey",
        "policy_decisions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "policy_decisions_agent_id_fkey",
        "policy_decisions",
        "agents",
        ["agent_id"],
        ["agent_id"],
        ondelete="CASCADE",
    )

    # ── approval_requests: drop old FK, re-add with ON DELETE CASCADE ─────────
    op.drop_constraint(
        "approval_requests_agent_id_fkey",
        "approval_requests",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "approval_requests_agent_id_fkey",
        "approval_requests",
        "agents",
        ["agent_id"],
        ["agent_id"],
        ondelete="CASCADE",
    )

    # ── approval_requests: composite index for the SLA expiry background loop ─
    # Query: WHERE status = 'pending' AND expires_at <= now()
    op.create_index(
        "ix_approval_status_expires",
        "approval_requests",
        ["status", "expires_at"],
    )

    # ── approval_requests: correlation_id index (present in ORM, not in 0001) ─
    op.create_index(
        "ix_approval_requests_correlation_id",
        "approval_requests",
        ["correlation_id"],
    )

    # ── drift_metrics: composite index for detector's recency window query ─────
    # Query: WHERE agent_id = ? AND created_at >= ?
    op.create_index(
        "ix_drift_metrics_agent_created",
        "drift_metrics",
        ["agent_id", "created_at"],
    )


def downgrade() -> None:
    # Remove new indexes
    op.drop_index("ix_drift_metrics_agent_created", table_name="drift_metrics")
    op.drop_index("ix_approval_requests_correlation_id", table_name="approval_requests")
    op.drop_index("ix_approval_status_expires", table_name="approval_requests")

    # Restore approval_requests FK without CASCADE
    op.drop_constraint(
        "approval_requests_agent_id_fkey",
        "approval_requests",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "approval_requests_agent_id_fkey",
        "approval_requests",
        "agents",
        ["agent_id"],
        ["agent_id"],
    )

    # Restore policy_decisions FK without CASCADE
    op.drop_constraint(
        "policy_decisions_agent_id_fkey",
        "policy_decisions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "policy_decisions_agent_id_fkey",
        "policy_decisions",
        "agents",
        ["agent_id"],
        ["agent_id"],
    )
