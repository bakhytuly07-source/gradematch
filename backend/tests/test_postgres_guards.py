"""Ensure opt-in PostgreSQL tests cannot connect without an explicit valid URL."""
import pytest

import test_postgres


def test_unset_postgres_url_skips_before_engine_creation(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unrelated/app")
    monkeypatch.setattr(test_postgres, "make_engine", lambda *_: pytest.fail("Unexpected connection attempt"))
    fixture = test_postgres.postgres.__wrapped__(monkeypatch)
    with pytest.raises(pytest.skip.Exception, match="Set TEST_DATABASE_URL"):
        next(fixture)


def test_non_postgres_test_url_fails_before_engine_creation(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(test_postgres, "make_engine", lambda *_: pytest.fail("Unexpected connection attempt"))
    fixture = test_postgres.postgres.__wrapped__(monkeypatch)
    with pytest.raises(pytest.fail.Exception, match="must use postgresql"):
        next(fixture)
