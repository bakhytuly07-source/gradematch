import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import CollectorRegistry, generate_latest

from app.main import create_app
from app.metrics import BusinessMetrics, views, RENDER_BUCKETS, REASONS
from app.color import MAX_BYTES
from test_api import SETTINGS, image_bytes, register


@pytest.fixture
def measured(monkeypatch):
    monkeypatch.delenv('OTEL_EXPORTER_OTLP_ENDPOINT', raising=False)
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader], views=views())
    app = create_app()
    app.state.business_metrics = BusinessMetrics(provider.get_meter('test'))
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, reader
    provider.shutdown()


def points(reader):
    data = reader.get_metrics_data()
    return {metric.name: metric.data.data_points for r in data.resource_metrics for s in r.scope_metrics for metric in s.metrics} if data else {}


def value(reader, name, reason=None):
    return sum(p.value for p in points(reader).get('gradematch_' + name, ())
               if reason is None or p.attributes.get('reason') == reason)


def test_success_and_rejections(measured):
    client, reader = measured
    assert value(reader, 'users_registered') == 0
    headers = register(client)
    assert value(reader, 'users_registered') == 1
    assert client.post('/api/auth/register', json={'email': 'user@example.com', 'password': 'password123'}).status_code == 409
    assert client.post('/api/auth/register', json={}).status_code == 422
    assert value(reader, 'users_registered') == 1
    body = {**SETTINGS, 'name': 'x', 'thumbnail': ''}
    assert client.post('/api/looks', json=body).status_code == 401
    assert client.post('/api/looks', headers=headers, json={}).status_code == 422
    assert value(reader, 'looks_saved') == 0
    assert client.post('/api/looks', headers=headers, json=body).status_code == 201
    assert value(reader, 'looks_saved') == 1
    assert client.post('/api/generate', files={'referenceFile': ('photo.png', image_bytes())}).status_code == 200
    assert value(reader, 'styles_generated') == 1
    assert value(reader, 'generate_failures') == 0
    assert client.post('/api/render-lut', json={}).status_code == 422
    assert 'gradematch_lut_render_seconds' not in points(reader)
    assert client.post('/api/render-lut', json=SETTINGS).status_code == 200
    p, = points(reader)['gradematch_lut_render_seconds']
    assert p.count == 1 and p.sum >= 0
    assert p.explicit_bounds == RENDER_BUCKETS


@pytest.mark.parametrize('case,reason,status', [
    ('missing', 'invalid_request', 422), ('malformed', 'invalid_request', 422),
    ('large', 'too_large', 413), ('corrupt', 'invalid_image', 422),
    ('unsupported', 'invalid_image', 415), ('exception', 'processing_error', 500)])
def test_generate_failures(measured, monkeypatch, case, reason, status):
    client, reader = measured
    kwargs = {}
    if case == 'malformed':
        kwargs = {'content': b'broken', 'headers': {'Content-Type': 'multipart/form-data; boundary=x'}}
    if case in {'large', 'corrupt', 'unsupported', 'exception'}:
        data = {'large': b'x' * (MAX_BYTES + 1), 'corrupt': b'\x89PNG\r\n\x1a\ninvalid',
                'unsupported': image_bytes('GIF'), 'exception': image_bytes()}[case]
        kwargs = {'files': {'referenceFile': ('private-user-image.jpg', data)}}
    if case == 'exception':
        def fail(*args):
            raise RuntimeError('private exception text')
        monkeypatch.setattr('app.main.analyze', fail)
    before = value(reader, 'generate_failures')
    assert client.post('/api/generate', **kwargs).status_code == status
    assert value(reader, 'generate_failures') == before + 1
    assert value(reader, 'generate_failures', reason) == 1
    assert value(reader, 'styles_generated') == 0
    for p in points(reader)['gradematch_generate_failures']:
        assert p.attributes['reason'] in REASONS
        assert set(p.attributes) == {'environment', 'version', 'reason'}


@pytest.mark.parametrize('custom', [False, True])
def test_prometheus_export(monkeypatch, custom):
    for key, val in [('DEPLOYMENT_ENVIRONMENT', 'qa'), ('APP_VERSION', 'test-build')]:
        if custom:
            monkeypatch.setenv(key, val)
        else:
            monkeypatch.delenv(key, raising=False)
    registry = CollectorRegistry()
    reader = PrometheusMetricReader(disable_target_info=True, registry=registry)
    provider = MeterProvider(metric_readers=[reader], views=views())
    metrics = BusinessMetrics(provider.get_meter('contract'))
    for name in metrics.counters:
        metrics.add(name, 'invalid_request' if name == 'generate_failures' else None)
    metrics.rendered(.02)
    text = generate_latest(registry).decode()
    expected = ['gradematch_' + n + '_total' for n in metrics.counters]
    expected += ['gradematch_lut_render_seconds_' + suffix for suffix in ('bucket', 'count', 'sum')]
    for name in expected:
        lines = [line for line in text.splitlines() if line.startswith(name + '{')]
        assert lines, text
        for line in lines:
            assert 'environment="' + ('qa' if custom else 'local') + '"' in line
            assert 'version="' + ('test-build' if custom else 'dev') + '"' in line
    provider.shutdown()


def test_database_failures_do_not_count(client, monkeypatch):
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader], views=views())
    client.app.state.business_metrics = BusinessMetrics(provider.get_meter('db-fail'))
    headers = register(client)
    assert value(reader, 'users_registered') == 1
    from sqlalchemy.orm import Session
    def fail(*args, **kwargs):
        raise RuntimeError('database unavailable')
    monkeypatch.setattr(Session, 'commit', fail)
    assert client.post('/api/auth/register', json={'email': 'next@example.com', 'password': 'password123'}).status_code == 500
    assert value(reader, 'users_registered') == 1
    assert client.post('/api/looks', headers=headers, json={**SETTINGS, 'name': 'x', 'thumbnail': ''}).status_code == 500
    assert value(reader, 'looks_saved') == 0
    provider.shutdown()


def test_committed_orm_successes(client):
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader], views=views())
    client.app.state.business_metrics = BusinessMetrics(provider.get_meter('orm-success'))
    assert value(reader, 'users_registered') == 0
    headers = register(client)
    assert value(reader, 'users_registered') == 1
    assert value(reader, 'looks_saved') == 0
    assert client.post('/api/looks', headers=headers, json={**SETTINGS, 'name': 'saved', 'thumbnail': ''}).status_code == 201
    assert value(reader, 'looks_saved') == 1
    provider.shutdown()
