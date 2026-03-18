from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime (replaces deprecated datetime.utcnow())."""
    return datetime.now(tz=timezone.utc)


def iso_utcnow() -> str:
    """Return current UTC time as ISO8601 string with timezone."""
    return utcnow().isoformat()
