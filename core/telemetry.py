import os
import logging
from threading import Lock

logger = logging.getLogger(__name__)

_init_lock = Lock()
_is_initialized = False


def init_telemetry() -> None:
    global _is_initialized

    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        return

    with _init_lock:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.instrumentation.django import DjangoInstrumentor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
        except Exception as exc:
            # Do not block app startup if tracing dependencies are missing.
            logger.warning("Telemetry disabled due to import error: %s", exc)
            return

        service_name = os.getenv("OTEL_SERVICE_NAME", "uevent-backend")
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318/v1/traces")

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))

        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(provider)
        DjangoInstrumentor().instrument()

        _is_initialized = True
