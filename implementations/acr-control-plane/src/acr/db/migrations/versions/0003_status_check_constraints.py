"""Add CHECK constraints on status/decision/action_type enum-like columns.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-16

Changes:
  - policy_decisions.decision: CHECK IN ('allow', 'deny', 'escalate')
  - approval_requests.status: CHECK IN ('pending', 'approved', 'denied', 'overridden', 'timed_out')
  - approval_requests.decision: CHECK IS NULL OR IN ('approved', 'denied', 'overridden')
  - containment_actions.action_type: CHECK IN ('kill', 'restore', 'throttle', 'restrict', 'isolate')
"""
from __future__ import annotations

from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── policy_decisions.decision ─────────────────────────────────────────────
    op.create_check_constraint(
        "ck_policy_decisions_decision",
        "policy_decisions",
        "decision IN ('allow', 'deny', 'escalate')",
    )

    # ── approval_requests.status ──────────────────────────────────────────────
    op.create_check_constraint(
        "ck_approval_requests_status",
        "approval_requests",
        "status IN ('pending', 'approved', 'denied', 'overridden', 'timed_out')",
    )

    # ── approval_requests.decision (nullable) ─────────────────────────────────
    op.create_check_constraint(
        "ck_approval_requests_decision",
        "approval_requests",
        "decision IS NULL OR decision IN ('approved', 'denied', 'overridden')",
    )

    # ── containment_actions.action_type ───────────────────────────────────────
    op.create_check_constraint(
        "ck_containment_actions_action_type",
        "containment_actions",
        "action_type IN ('kill', 'restore', 'throttle', 'restrict', 'isolate')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_containment_actions_action_type", "containment_actions", type_="check"
    )
    op.drop_constraint(
        "ck_approval_requests_decision", "approval_requests", type_="check"
    )
    op.drop_constraint(
        "ck_approval_requests_status", "approval_requests", type_="check"
    )
    op.drop_constraint(
        "ck_policy_decisions_decision", "policy_decisions", type_="check"
    )
