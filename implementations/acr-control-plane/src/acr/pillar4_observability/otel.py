"""Pillar 4: OpenTelemetry trace/span/metrics integration."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import metrics, propagate, trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace.status import StatusCode

from acr.config import settings

_tracer: trace.Tracer | None = None
_meter: metrics.Meter | None = None


def setup_otel() -> None:
    """Initialize OpenTelemetry SDK. Called once at startup."""
    global _tracer, _meter

    resource = Resource.create({"service.name": settings.otel_service_name})

    # ── TracerProvider ────────────────────────────────────────────────────────
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("acr.control_plane")

    # ── MeterProvider ─────────────────────────────────────────────────────────
    if settings.otel_exporter_otlp_endpoint:
        metric_exporter = OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    else:
        meter_provider = MeterProvider(resource=resource)

    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter("acr.control_plane")

    # Create standard ACR metrics
    _meter.create_counter(
        "acr.evaluate.total",
        description="Total evaluate requests",
    )
    _meter.create_histogram(
        "acr.evaluate.latency",
        description="Evaluate request latency in ms",
        unit="ms",
    )
    _meter.create_counter(
        "acr.approval.total",
        description="Total approval requests",
    )
    _meter.create_counter(
        "acr.containment.kills",
        description="Total kill switch activations",
    )

    # ── W3C Trace Context Propagation ─────────────────────────────────────────
    propagate.set_global_textmap(
        CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()])
    )

    # ── Auto-instrumentation: HTTPX ───────────────────────────────────────────
    HTTPXClientInstrumentor().instrument()


def setup_telemetry(app: Any, engine: Any = None) -> None:
    """Instrument FastAPI app and optional SQLAlchemy engine after setup_otel()."""
    FastAPIInstrumentor.instrument_app(app)
    if engine is not None:
        sync_engine = getattr(engine, "sync_engine", engine)
        SQLAlchemyInstrumentor().instrument(engine=sync_engine)


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        return trace.get_tracer("acr.control_plane")
    return _tracer


def get_meter() -> metrics.Meter:
    if _meter is None:
        return metrics.get_meter("acr.control_plane")
    return _meter


@contextmanager
def acr_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[trace.Span, None, None]:
    """Context manager that creates a named ACR span with error recording."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
