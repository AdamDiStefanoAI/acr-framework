"""Convert telemetry_events and drift_metrics to monthly range partitioning

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-07
"""
from __future__ import annotations

from datetime import date

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _first_of_month(value: date) -> date:
    return value.replace(day=1)


def _add_months(value: date, months: int) -> date:
    month_index = (value.year * 12 + value.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _partition_bounds(conn, table: str) -> tuple[date, date]:
    result = conn.execute(
        sa.text(
            f"SELECT MIN(created_at)::date AS min_created, "
            f"MAX(created_at)::date AS max_created FROM {table}"
        )
    )
    row = result.fetchone()
    today = date.today()
    min_created = row.min_created if row and row.min_created else today
    max_created = row.max_created if row and row.max_created else today

    start = _first_of_month(min_created)
    # Keep a forward partition horizon even for mostly historical data.
    end = _add_months(_first_of_month(max_created), 4)
    return start, end


def _create_partitioned_copy(conn, table: str, tmp: str) -> None:
    # Do not copy constraints or indexes onto the partitioned parent; Postgres
    # rejects inherited PK/UNIQUE constraints that do not include created_at.
    op.execute(
        f"CREATE TABLE {tmp} ("
        f"LIKE {table} INCLUDING DEFAULTS INCLUDING GENERATED "
        f"INCLUDING IDENTITY INCLUDING STORAGE INCLUDING COMMENTS"
        f") PARTITION BY RANGE (created_at)"
    )

    start, end = _partition_bounds(conn, table)
    cursor = start
    while cursor < end:
        next_month = _add_months(cursor, 1)
        suffix = f"y{cursor.year:04d}m{cursor.month:02d}"
        part_name = f"{table}_{suffix}"
        op.execute(
            f"CREATE TABLE {part_name} PARTITION OF {tmp} "
            f"FOR VALUES FROM ('{cursor.isoformat()}') TO ('{next_month.isoformat()}')"
        )
        cursor = next_month

    op.execute(f"CREATE TABLE {table}_default PARTITION OF {tmp} DEFAULT")


def _create_indexes(table: str) -> None:
    if table == "telemetry_events":
        op.create_index("ix_telemetry_events_event_id", table, ["event_id"])
        op.create_index("ix_telemetry_events_correlation_id", table, ["correlation_id"])
        op.create_index("ix_telemetry_events_agent_id", table, ["agent_id"])
        op.create_index("ix_telemetry_events_created_at", table, ["created_at"])
        return

    if table == "drift_metrics":
        op.create_index("ix_drift_metrics_agent_id", table, ["agent_id"])
        op.create_index("ix_drift_metrics_created_at", table, ["created_at"])
        op.create_index("ix_drift_metrics_agent_created", table, ["agent_id", "created_at"])
        return

    raise ValueError(f"unsupported partitioned table: {table}")


def upgrade() -> None:
    conn = op.get_bind()

    for table in ("telemetry_events", "drift_metrics"):
        # Check if table is already partitioned (Postgres-specific)
        result = conn.execute(
            sa.text(
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

        # 1. Create a partitioned copy without invalid inherited constraints.
        _create_partitioned_copy(conn, table, tmp)

        # 2. Migrate data
        op.execute(f"INSERT INTO {tmp} SELECT * FROM {table}")

        # 3. Swap tables and recreate parent indexes.
        op.execute(f"DROP TABLE {table}")
        op.execute(f"ALTER TABLE {tmp} RENAME TO {table}")
        _create_indexes(table)


def downgrade() -> None:
    # Partitioned tables remain partitioned; full reversal requires manual intervention.
    # This downgrade creates standard (non-partitioned) tables and copies data back.
    conn = op.get_bind()

    for table in ("telemetry_events", "drift_metrics"):
        result = conn.execute(
            sa.text(
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
