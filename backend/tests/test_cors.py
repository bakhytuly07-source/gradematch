import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.cors import allowed_origins


def test_default_override_and_wildcard_rejection(monkeypatch):
    monkeypatch.delenv('CORS_ORIGINS', raising=False)
    assert allowed_origins() == ['http://localhost:5173']
    for invalid in ['*', 'https://*.example.com', 'https://example.com/path']:
        monkeypatch.setenv('CORS_ORIGINS', invalid)
        with pytest.raises(ValueError):
            allowed_origins()
    monkeypatch.setenv('CORS_ORIGINS', '')
    assert allowed_origins() == []


def test_preflight_and_error_headers(monkeypatch):
    monkeypatch.setenv('CORS_ORIGINS', ' http://localhost:5173, https://app.example.com ')
    with TestClient(create_app()) as client:
        for origin in ['http://localhost:5173', 'https://app.example.com']:
            for path, method, headers in [('/api/generate', 'POST', 'content-type'),
                    ('/api/looks', 'POST', 'authorization,content-type'),
                    ('/api/looks/id', 'PATCH', 'authorization,content-type'),
                    ('/api/looks/id', 'DELETE', 'authorization')]:
                response = client.options(path, headers={'Origin': origin,
                    'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': headers})
                assert response.status_code == 200
                assert response.headers['access-control-allow-origin'] == origin
                assert method in response.headers['access-control-allow-methods']
            for path, status in [('/api/auth/me', 401), ('/api/render-lut', 422)]:
                response = client.get(path, headers={'Origin': origin}) if status == 401 else client.post(path, json={}, headers={'Origin': origin})
                assert response.status_code == status
                assert response.headers['access-control-allow-origin'] == origin
        response = client.options('/api/looks', headers={'Origin':'https://evil.example',
            'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization'})
        assert response.status_code == 400
        assert 'access-control-allow-origin' not in response.headers
        denied = client.get('/api/auth/me', headers={'Origin':'https://evil.example'})
        assert denied.status_code == 401
        assert 'access-control-allow-origin' not in denied.headers
