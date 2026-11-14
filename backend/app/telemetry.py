"""Opt-in, app-scoped OTLP telemetry. Never capture request payloads or headers."""
import logging
import os
from contextlib import asynccontextmanager

from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import SpanKind


def resource():
    return Resource.create({
        "service.name": "gradematch",
        "deployment.environment": os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
        "service.version": os.getenv("APP_VERSION", "dev"),
    })


class Telemetry:
    def __init__(self, traces, metrics, logs):
        self.traces, self.metrics, self.logs = traces, metrics, logs
        self.tracer = traces.get_tracer("gradematch")
        self.meter = metrics.get_meter("gradematch")
        from opentelemetry.sdk._logs import LoggingHandler
        self.log_handler = LoggingHandler(logger_provider=logs)
        self.requests = self.meter.create_counter("gradematch.http.requests")

    def shutdown(self):
        for provider in (self.traces, self.metrics, self.logs):
            provider.shutdown()


def configure(application):
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    application.state.telemetry = None
    application.state.business_metrics = None
    if not endpoint:
        return
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

    identity = resource()
    traces = TracerProvider(resource=identity)
    traces.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
        endpoint=endpoint.rstrip("/") + "/v1/traces", timeout=1), max_queue_size=256, max_export_batch_size=64))
    from .metrics import BusinessMetrics, views
    metrics = MeterProvider(resource=identity, views=views(), metric_readers=[PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint.rstrip("/") + "/v1/metrics", timeout=1),
        export_interval_millis=5000, export_timeout_millis=1500)])
    logs = LoggerProvider(resource=identity)
    logs.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(
        endpoint=endpoint.rstrip("/") + "/v1/logs", timeout=1), max_queue_size=256, max_export_batch_size=64))
    telemetry = Telemetry(traces, metrics, logs)
    application.state.telemetry = telemetry
    application.state.business_metrics = BusinessMetrics(telemetry.meter)
    if application.state.engine is not None:
        from sqlalchemy import event
        # Engine-local events avoid global monkeypatching and never export SQL,
        # bind parameters, connection strings or exception messages.
        @event.listens_for(application.state.engine, "before_cursor_execute")
        def before(conn, cursor, statement, parameters, context, executemany):
            context._telemetry_span = telemetry.tracer.start_span("SQLAlchemy query", kind=SpanKind.CLIENT,
                attributes={"db.system": application.state.engine.dialect.name})
        @event.listens_for(application.state.engine, "after_cursor_execute")
        def after(conn, cursor, statement, parameters, context, executemany):
            context._telemetry_span.end()
        @event.listens_for(application.state.engine, "handle_error")
        def failed(context):
            span = getattr(context.execution_context, "_telemetry_span", None)
            if span is not None:
                from opentelemetry.trace import Status, StatusCode
                span.set_status(Status(StatusCode.ERROR))
                span.end()

    @application.middleware("http")
    async def request_telemetry(request, call_next):
        # Manual span lifecycle deliberately excludes exception events, query strings,
        # headers and URLs, any of which could contain credentials or uploaded data.
        span = telemetry.tracer.start_span("HTTP " + request.method, kind=SpanKind.SERVER)
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode
        status = 500
        try:
            with trace.use_span(span, end_on_exit=False, record_exception=False,
                                set_status_on_exception=False):
                response = await call_next(request)
                status = response.status_code
                return response
        finally:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            span.update_name(request.method + " " + route)
            span.set_attributes({"http.request.method": request.method,
                                 "http.route": route, "http.response.status_code": status})
            if status >= 500:
                span.set_status(Status(StatusCode.ERROR))
            span.end()
            telemetry.requests.add(1, {"http.route": route, "http.response.status_code": status})
            telemetry.log_handler.handle(logging.LogRecord(
                "gradematch.requests", logging.INFO, "", 0, "API request completed", (), None))

    previous = application.router.lifespan_context
    @asynccontextmanager
    async def lifespan(app):
        async with previous(app):
            try:
                yield
            finally:
                telemetry.shutdown()
    application.router.lifespan_context = lifespan
