"""Optional SPA hosting must preserve API routing and directory boundaries."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def static_dir(tmp_path):
    public = tmp_path / 'public'
    public.mkdir()
    (public / '_shell.html').write_text('<!doctype html><title>GradeMatch shell</title>')
    (public / 'assets').mkdir()
    (public / 'assets/app.js').write_text('console.log("asset")')
    (tmp_path / 'secret.txt').write_text('private secret')
    (public / 'escape.txt').symlink_to(tmp_path / 'secret.txt')
    return public


@pytest.mark.parametrize('setting', [None, '/nonexistent/gradematch/static'])
def test_disabled(monkeypatch, setting):
    if setting is None:
        monkeypatch.delenv('STATIC_DIR', raising=False)
    else:
        monkeypatch.setenv('STATIC_DIR', setting)
    with TestClient(create_app()) as client:
        for path in ['/', '/login', '/unknown', '/api/unknown']:
            response = client.get(path)
            assert response.status_code == 404
            assert response.json() == {'code': 'not_found', 'message': 'Not Found'}


def test_static_routes(monkeypatch, static_dir):
    monkeypatch.setenv('STATIC_DIR', str(static_dir))
    with TestClient(create_app()) as client:
        for path in ['/', '/login', '/library', '/register']:
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers['content-type'].startswith('text/html')
            assert 'GradeMatch shell' in response.text
        asset = client.get('/assets/app.js')
        assert asset.status_code == 200
        assert 'javascript' in asset.headers['content-type']
        assert asset.text == 'console.log("asset")'
        for path in ['/api', '/api/unknown', '/assets/missing.js', '/assets/missing',
                     '/missing.js', '/escape.txt', '/%2e%2e/secret.txt']:
            response = client.get(path)
            assert response.status_code == 404
            assert set(response.json()) == {'code', 'message'}
        assert client.get('/docs').status_code == 200
        assert client.get('/api/auth/me').status_code == 401
        schema = client.get('/openapi.json').json()
        assert all(path.startswith('/api/') for path in schema['paths'])
        assert sum(len(operations) for operations in schema['paths'].values()) == 13
