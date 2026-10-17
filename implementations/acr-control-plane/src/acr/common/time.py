from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime (replaces deprecated datetime.utcnow())."""
    return datetime.now(tz=UTC)


def iso_utcnow() -> str:
    """Return current UTC time as ISO8601 string with timezone."""
    return utcnow().isoformat()
