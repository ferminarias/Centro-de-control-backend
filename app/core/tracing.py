"""
OpenTelemetry distributed tracing configuration.

Instruments FastAPI and SQLAlchemy automatically.
Exports traces to an OTLP-compatible backend (Jaeger, Tempo, etc.)
configured via the OTEL_EXPORTER_OTLP_ENDPOINT environment variable.

Usage:
    Call setup_tracing(app) once during application startup,
    after the FastAPI app is created.

Environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT  gRPC endpoint for the OTLP collector
                                  e.g. "http://jaeger:4317"
                                  Defaults to None (tracing disabled).
    OTEL_SERVICE_NAME            Service name in trace UI (default: centro-control)
"""
import logging
import os

logger = logging.getLogger(__name__)

_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "centro-control")


def setup_tracing(app) -> None:
    """
    Configure OpenTelemetry tracing for a FastAPI application.

    No-ops gracefully if the OTLP endpoint is not configured or if
    opentelemetry packages are not installed.
    """
    if not _OTLP_ENDPOINT:
        logger.info("Tracing disabled — set OTEL_EXPORTER_OTLP_ENDPOINT to enable")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    except ImportError:
        logger.warning(
            "opentelemetry packages not installed — tracing disabled. "
            "Run: pip install opentelemetry-sdk opentelemetry-instrumentation-fastapi "
            "opentelemetry-instrumentation-sqlalchemy opentelemetry-exporter-otlp-proto-grpc"
        )
        return

    resource = Resource.create({"service.name": _SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=_OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI (adds span per request)
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument SQLAlchemy (adds span per query)
    SQLAlchemyInstrumentor().instrument(enable_commenter=True, commenter_options={})

    logger.info(
        "OpenTelemetry tracing enabled — service=%s endpoint=%s",
        _SERVICE_NAME,
        _OTLP_ENDPOINT,
    )
