"""Allow MODIFY decisions in policy_decisions.

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-08
"""

from __future__ import annotations

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_policy_decisions_decision", "policy_decisions", type_="check")
    op.create_check_constraint(
        "ck_policy_decisions_decision",
        "policy_decisions",
        "decision IN ('allow', 'deny', 'modify', 'escalate')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_policy_decisions_decision", "policy_decisions", type_="check")
    op.create_check_constraint(
        "ck_policy_decisions_decision",
        "policy_decisions",
        "decision IN ('allow', 'deny', 'escalate')",
    )
