"""Gateway middleware: correlation ID injection and request timing."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from acr.common.correlation import set_correlation_id

logger = structlog.get_logger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Injects a correlation ID into every request and adds it to the response header.
    Sets structlog context so all log lines within the request include the correlation_id.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Prefer caller-supplied correlation ID; generate one if absent
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(cid)

        # Bind to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=cid)

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        response.headers["X-Correlation-ID"] = cid
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response
