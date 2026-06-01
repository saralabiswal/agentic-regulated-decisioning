# Author: Sarala Biswal
"""OpenTelemetry tracing setup."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


def configure_tracing(service_name: str = "agentic-regulated-decisioning") -> dict:
    """Configure OpenTelemetry tracing and return setup status."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:
        return {"service_name": service_name, "configured": False}

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return {"service_name": service_name, "configured": True}


def instrument_fastapi(app: Any) -> bool:
    """Attach FastAPI tracing middleware when instrumentation is available."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except Exception:
        return False
    FastAPIInstrumentor.instrument_app(app)
    return True


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Create a tracing span or a no-op span when tracing is unavailable."""
    try:
        from opentelemetry import trace
    except Exception:
        yield None
        return

    tracer = trace.get_tracer("agentic-regulated-decisioning")
    with tracer.start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            if isinstance(value, str | bool | int | float):
                span.set_attribute(key, value)
            elif value is not None:
                span.set_attribute(key, str(value))
        yield span
