"""Regression checks for the PostgreSQL monthly-partition migration."""

from __future__ import annotations

from datetime import date
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

monthly_partitioning = import_module("acr.db.migrations.versions.0011_monthly_partitioning")


class _FixedDate(date):
    @classmethod
    def today(cls) -> date:
        return date(2026, 10, 17)


@pytest.mark.parametrize(
    ("value", "months", "expected"),
    [
        (date(2026, 12, 31), 1, date(2027, 1, 1)),
        (date(2024, 2, 29), 1, date(2024, 3, 1)),
        (date(2026, 1, 15), -1, date(2025, 12, 1)),
        (date(2026, 10, 17), 0, date(2026, 10, 1)),
    ],
)
def test_month_arithmetic(value, months, expected) -> None:
    assert monthly_partitioning._add_months(value, months) == expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (None, (date(2026, 10, 1), date(2027, 2, 1))),
        (
            SimpleNamespace(min_created=None, max_created=None),
            (date(2026, 10, 1), date(2027, 2, 1)),
        ),
        (
            SimpleNamespace(min_created=date(2024, 2, 29), max_created=date(2025, 12, 31)),
            (date(2024, 2, 1), date(2026, 4, 1)),
        ),
    ],
)
def test_partition_bounds_preserve_dates_and_empty_table_fallback(
    monkeypatch, row, expected
) -> None:
    monkeypatch.setattr(monthly_partitioning, "date", _FixedDate)
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = row

    assert monthly_partitioning._partition_bounds(conn, "telemetry_events") == expected

    statement = conn.execute.call_args.args[0]
    assert isinstance(statement, sa.sql.Select)
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "CAST(min(telemetry_events.created_at) AS DATE) AS min_created" in sql
    assert "CAST(max(telemetry_events.created_at) AS DATE) AS max_created" in sql
    assert statement.get_final_froms()[0].name == "telemetry_events"


@pytest.mark.parametrize(
    "table_name",
    [
        "drift_metrics",
        'telemetry_events"; DROP TABLE drift_metrics; --',
        "public.telemetry_events",
    ],
)
def test_partition_bounds_treat_table_name_as_one_identifier(table_name) -> None:
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = None

    monthly_partitioning._partition_bounds(conn, table_name)

    statement = conn.execute.call_args.args[0]
    dialect = postgresql.dialect()
    quoted_name = dialect.identifier_preparer.quote(table_name)
    sql = str(statement.compile(dialect=dialect))
    assert sql.endswith("FROM " + quoted_name)
    assert statement.get_final_froms()[0].name == table_name
    assert len(statement.get_final_froms()) == 1
    assert not isinstance(statement, sa.sql.elements.TextClause)


def test_partitioned_copy_has_contiguous_months_and_default_partition(monkeypatch) -> None:
    operations = Mock()
    monkeypatch.setattr(monthly_partitioning, "op", operations)
    monkeypatch.setattr(
        monthly_partitioning,
        "_partition_bounds",
        Mock(return_value=(date(2024, 1, 1), date(2024, 4, 1))),
    )

    monthly_partitioning._create_partitioned_copy(
        Mock(), "telemetry_events", "telemetry_events_new"
    )

    statements = [item.args[0] for item in operations.execute.call_args_list]
    assert statements == [
        "CREATE TABLE telemetry_events_new (LIKE telemetry_events INCLUDING DEFAULTS "
        "INCLUDING GENERATED INCLUDING IDENTITY INCLUDING STORAGE INCLUDING COMMENTS) "
        "PARTITION BY RANGE (created_at)",
        "CREATE TABLE telemetry_events_y2024m01 PARTITION OF telemetry_events_new "
        "FOR VALUES FROM ('2024-01-01') TO ('2024-02-01')",
        "CREATE TABLE telemetry_events_y2024m02 PARTITION OF telemetry_events_new "
        "FOR VALUES FROM ('2024-02-01') TO ('2024-03-01')",
        "CREATE TABLE telemetry_events_y2024m03 PARTITION OF telemetry_events_new "
        "FOR VALUES FROM ('2024-03-01') TO ('2024-04-01')",
        "CREATE TABLE telemetry_events_default PARTITION OF telemetry_events_new DEFAULT",
    ]
    # A parent PK/UNIQUE copied without created_at is invalid in PostgreSQL.
    assert "INCLUDING ALL" not in statements[0]
    assert "INCLUDING INDEXES" not in statements[0]
    assert "INCLUDING CONSTRAINTS" not in statements[0]


@pytest.mark.parametrize(
    ("table", "expected_indexes"),
    [
        (
            "telemetry_events",
            [
                ("ix_telemetry_events_event_id", ["event_id"]),
                ("ix_telemetry_events_correlation_id", ["correlation_id"]),
                ("ix_telemetry_events_agent_id", ["agent_id"]),
                ("ix_telemetry_events_created_at", ["created_at"]),
            ],
        ),
        (
            "drift_metrics",
            [
                ("ix_drift_metrics_agent_id", ["agent_id"]),
                ("ix_drift_metrics_created_at", ["created_at"]),
                ("ix_drift_metrics_agent_created", ["agent_id", "created_at"]),
            ],
        ),
    ],
)
def test_parent_indexes_are_recreated(monkeypatch, table, expected_indexes) -> None:
    operations = Mock()
    monkeypatch.setattr(monthly_partitioning, "op", operations)

    monthly_partitioning._create_indexes(table)

    assert operations.create_index.call_args_list == [
        call(name, table, columns) for name, columns in expected_indexes
    ]


def test_unknown_table_indexes_are_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported partitioned table"):
        monthly_partitioning._create_indexes("unexpected_table")


def test_upgrade_copies_data_before_swapping_and_skips_existing_partitions(monkeypatch) -> None:
    operations = Mock()
    conn = operations.get_bind.return_value
    conn.execute.return_value.fetchone.side_effect = [("r",), ("p",)]
    monkeypatch.setattr(monthly_partitioning, "op", operations)
    create_copy = Mock()
    create_indexes = Mock()
    monkeypatch.setattr(monthly_partitioning, "_create_partitioned_copy", create_copy)
    monkeypatch.setattr(monthly_partitioning, "_create_indexes", create_indexes)

    monthly_partitioning.upgrade()

    create_copy.assert_called_once_with(conn, "telemetry_events", "telemetry_events_new")
    assert operations.execute.call_args_list == [
        call("INSERT INTO telemetry_events_new SELECT * FROM telemetry_events"),
        call("DROP TABLE telemetry_events"),
        call("ALTER TABLE telemetry_events_new RENAME TO telemetry_events"),
    ]
    create_indexes.assert_called_once_with("telemetry_events")
    assert [item.args[1] for item in conn.execute.call_args_list] == [
        {"tbl": "telemetry_events"},
        {"tbl": "drift_metrics"},
    ]


@pytest.mark.parametrize("other_table", [None, ("r",)])
def test_downgrade_flattens_only_partitioned_tables(monkeypatch, other_table) -> None:
    operations = Mock()
    conn = operations.get_bind.return_value
    conn.execute.return_value.fetchone.side_effect = [("p",), other_table]
    monkeypatch.setattr(monthly_partitioning, "op", operations)

    monthly_partitioning.downgrade()

    assert operations.execute.call_args_list == [
        call("CREATE TABLE telemetry_events_flat (LIKE telemetry_events INCLUDING ALL)"),
        call("INSERT INTO telemetry_events_flat SELECT * FROM telemetry_events"),
        call("DROP TABLE telemetry_events CASCADE"),
        call("ALTER TABLE telemetry_events_flat RENAME TO telemetry_events"),
    ]
