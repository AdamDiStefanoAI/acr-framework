from __future__ import annotations

import uuid
from contextvars import ContextVar

# Thread/async-local store for the current correlation ID
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def new_correlation_id() -> str:
    """Generate a new UUID v4 correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(cid: str) -> None:
    _correlation_id_var.set(cid)


def get_correlation_id() -> str:
    cid = _correlation_id_var.get()
    if not cid:
        cid = new_correlation_id()
        _correlation_id_var.set(cid)
    return cid
