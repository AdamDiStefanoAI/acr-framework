"""Pillar 4: OpenTelemetry trace/span integration."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from acr.config import settings

_tracer: trace.Tracer | None = None


def setup_otel() -> None:
    """Initialize OpenTelemetry SDK. Called once at startup."""
    global _tracer

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    else:
        # Development fallback: no-op (don't print spans to console by default)
        exporter = None  # type: ignore[assignment]

    if exporter:
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("acr.control_plane")


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        return trace.get_tracer("acr.control_plane")
    return _tracer


@contextmanager
def acr_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[trace.Span, None, None]:
    """Context manager that creates a named ACR span."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        yield span
