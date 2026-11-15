"""Deployed commit must override image defaults in every telemetry signal."""
from app.telemetry import app_version, resource
from app.metrics import BusinessMetrics
from unittest.mock import Mock


def test_actual_older_render_commit_overrides_build_version(monkeypatch):
    monkeypatch.setenv('RENDER_GIT_COMMIT', '123abcd' + '0' * 33)
    monkeypatch.setenv('APP_VERSION', '7654321')
    monkeypatch.setenv('DEPLOYMENT_ENVIRONMENT', 'prod')
    assert app_version() == '123abcd'
    assert resource().attributes['service.version'] == '123abcd'
    assert resource().attributes['deployment.environment'] == 'prod'
    assert BusinessMetrics(Mock()).labels == {'environment': 'prod', 'version': '123abcd'}


def test_explicit_local_version_without_render(monkeypatch):
    monkeypatch.delenv('RENDER_GIT_COMMIT', raising=False)
    monkeypatch.setenv('APP_VERSION', 'abcdef0')
    assert app_version() == 'abcdef0'
    assert resource().attributes['service.version'] == 'abcdef0'
    assert BusinessMetrics(Mock()).labels['version'] == 'abcdef0'
