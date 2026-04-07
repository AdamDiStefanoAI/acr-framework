"""Convert telemetry_events and drift_metrics to monthly range partitioning

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-07
"""
from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    for table in ("telemetry_events", "drift_metrics"):
        # Check if table is already partitioned (Postgres-specific)
        result = conn.execute(
            __import__("sqlalchemy").text(
                "SELECT c.relkind FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = :tbl AND n.nspname = 'public'"
            ),
            {"tbl": table},
        )
        row = result.fetchone()
        if row and row[0] == "p":
            # Already partitioned — skip
            continue

        tmp = f"{table}_new"

        # 1. Create partitioned table with same schema
        op.execute(
            f"CREATE TABLE {tmp} (LIKE {table} INCLUDING ALL) "
            f"PARTITION BY RANGE (created_at)"
        )

        # 2. Create initial partitions: current month + next 3 months
        partitions = [
            ("2026-04-01", "2026-05-01", "y2026m04"),
            ("2026-05-01", "2026-06-01", "y2026m05"),
            ("2026-06-01", "2026-07-01", "y2026m06"),
            ("2026-07-01", "2026-08-01", "y2026m07"),
        ]
        for start, end, suffix in partitions:
            part_name = f"{table}_{suffix}"
            op.execute(
                f"CREATE TABLE {part_name} PARTITION OF {tmp} "
                f"FOR VALUES FROM ('{start}') TO ('{end}')"
            )
            op.execute(
                f"CREATE INDEX ix_{part_name}_created_at ON {part_name} (created_at)"
            )

        # 3. Migrate data
        op.execute(f"INSERT INTO {tmp} SELECT * FROM {table}")

        # 4. Swap tables
        op.execute(f"DROP TABLE {table}")
        op.execute(f"ALTER TABLE {tmp} RENAME TO {table}")


def downgrade() -> None:
    # Partitioned tables remain partitioned; full reversal requires manual intervention.
    # This downgrade creates standard (non-partitioned) tables and copies data back.
    conn = op.get_bind()

    for table in ("telemetry_events", "drift_metrics"):
        result = conn.execute(
            __import__("sqlalchemy").text(
                "SELECT c.relkind FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = :tbl AND n.nspname = 'public'"
            ),
            {"tbl": table},
        )
        row = result.fetchone()
        if not row or row[0] != "p":
            continue

        tmp = f"{table}_flat"
        op.execute(
            f"CREATE TABLE {tmp} (LIKE {table} INCLUDING ALL)"
        )
        op.execute(f"INSERT INTO {tmp} SELECT * FROM {table}")
        op.execute(f"DROP TABLE {table} CASCADE")
        op.execute(f"ALTER TABLE {tmp} RENAME TO {table}")
