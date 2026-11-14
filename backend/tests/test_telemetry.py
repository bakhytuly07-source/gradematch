import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from app.main import create_app
from app.models import Base
from test_api import SETTINGS, image_bytes


@pytest.mark.parametrize('endpoint', [None, ''])
def test_disabled(monkeypatch, endpoint, caplog):
    if endpoint is None:
        monkeypatch.delenv('OTEL_EXPORTER_OTLP_ENDPOINT', raising=False)
    else:
        monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', endpoint)
    before = {t.ident for t in threading.enumerate()}
    app = create_app()
    with TestClient(app) as client:
        assert client.get('/docs').status_code == 200
        assert app.state.telemetry is None
        with caplog.at_level(logging.WARNING):
            logging.getLogger('app').warning('normal logging')
    assert 'normal logging' in caplog.text
    assert {t.ident for t in threading.enumerate()} == before


@pytest.fixture
def collector(monkeypatch):
    records = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            message = {'/v1/traces': ExportTraceServiceRequest, '/v1/metrics': ExportMetricsServiceRequest,
                       '/v1/logs': ExportLogsServiceRequest}[self.path]()
            message.ParseFromString(self.rfile.read(int(self.headers['Content-Length'])))
            records.append((self.path, message))
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', f'http://127.0.0.1:{server.server_port}')
    yield records
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize('custom', [False, True])
def test_actual_otlp_scenario(collector, monkeypatch, tmp_path, custom):
    for key, value in [('DEPLOYMENT_ENVIRONMENT', 'qa'), ('APP_VERSION', 'test-build')]:
        if custom:
            monkeypatch.setenv(key, value)
        else:
            monkeypatch.delenv(key, raising=False)
    app = create_app(storage='orm', database_url=f'sqlite:///{tmp_path}/telemetry.db')
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        auth = client.post('/api/auth/register', json={'email': 'secret@example.com', 'password': 'Secret-password-123!'})
        assert auth.status_code == 201
        token = auth.json()['access_token']
        headers = {'Authorization': 'Bearer ' + token}
        assert client.post('/api/generate', headers=headers, files={'referenceFile': ('secret-photo.jpg', image_bytes(), 'image/jpeg')}).status_code == 200
        assert client.post('/api/looks', headers=headers, json={**SETTINGS, 'name': 'private-look', 'thumbnail': ''}).status_code == 201
        for provider in (app.state.telemetry.traces, app.state.telemetry.metrics, app.state.telemetry.logs):
            assert provider.force_flush()
    assert {p for p, _ in collector} == {'/v1/traces', '/v1/metrics', '/v1/logs'}
    for path, message in collector:
        groups = getattr(message, {'/v1/traces': 'resource_spans', '/v1/metrics': 'resource_metrics', '/v1/logs': 'resource_logs'}[path])
        for group in groups:
            attrs = {a.key: a.value.string_value for a in group.resource.attributes}
            assert attrs['service.name'] == 'gradematch'
            assert attrs['deployment.environment'] == ('qa' if custom else 'local')
            assert attrs['service.version'] == ('test-build' if custom else 'dev')
    spans = [s for p, m in collector if p == '/v1/traces' for r in m.resource_spans for scope in r.scope_spans for s in scope.spans]
    assert any(s.name == 'POST /api/generate' for s in spans)
    assert any(any(a.key == 'db.system' for a in s.attributes) for s in spans)
    exported = '\n'.join(str(m) for _, m in collector)
    for secret in (token, 'secret@example.com', 'Secret-password-123!', 'secret-photo.jpg', 'private-look', 'referenceFile', 'thumbnail_url'):
        assert secret not in exported


def test_unreachable_endpoint(monkeypatch):
    import time
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://127.0.0.1:1')
    app = create_app()
    start = time.monotonic()
    with TestClient(app) as client:
        assert client.get('/docs').status_code == 200
        assert client.post('/api/generate').status_code == 422
        for provider in (app.state.telemetry.traces, app.state.telemetry.metrics, app.state.telemetry.logs):
            provider.force_flush(timeout_millis=1500)
    assert time.monotonic() - start < 10
