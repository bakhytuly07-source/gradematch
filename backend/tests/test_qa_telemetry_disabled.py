"""Independent QA guard: disabled telemetry cannot instantiate providers or send HTTP."""
import logging
import threading

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize('endpoint', [None, ''])
def test_disabled_never_constructs_providers_or_sends(monkeypatch, caplog, endpoint):
    from app.main import create_app
    if endpoint is None:
        monkeypatch.delenv('OTEL_EXPORTER_OTLP_ENDPOINT', raising=False)
    else:
        monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', endpoint)

    def forbidden(*args, **kwargs):
        pytest.fail('Disabled telemetry constructed a provider/exporter or attempted HTTP')

    for module, names in [
        ('opentelemetry.sdk.trace', ['TracerProvider']),
        ('opentelemetry.sdk.metrics', ['MeterProvider']),
        ('opentelemetry.sdk._logs', ['LoggerProvider']),
        ('opentelemetry.exporter.otlp.proto.http.trace_exporter', ['OTLPSpanExporter']),
        ('opentelemetry.exporter.otlp.proto.http.metric_exporter', ['OTLPMetricExporter']),
        ('opentelemetry.exporter.otlp.proto.http._log_exporter', ['OTLPLogExporter']),
        ('requests.sessions', ['Session.send']),
    ]:
        for name in names:
            monkeypatch.setattr(module + '.' + name, forbidden)
    before = {t.ident for t in threading.enumerate()}
    app = create_app()
    with TestClient(app) as client:
        assert client.get('/docs').status_code == 200
        assert client.post('/api/generate').status_code == 422
        assert app.state.telemetry is None
        assert app.state.business_metrics is None
        with caplog.at_level(logging.WARNING):
            logging.getLogger('app').warning('QA normal logging works')
    assert 'QA normal logging works' in caplog.text
    assert {t.ident for t in threading.enumerate()} == before
