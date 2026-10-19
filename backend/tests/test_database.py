from unittest.mock import patch

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, DEFAULT_URL, database_url, get_db, make_engine
from app.main import create_app
from app.models import User


def test_urls(tmp_path, monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    assert database_url() == DEFAULT_URL
    url = f"sqlite:///{tmp_path / 'other.db'}"
    monkeypatch.setenv('DATABASE_URL', url)
    engine = make_engine()
    assert str(engine.url) == url
    engine.dispose()
    with patch('app.database.create_engine') as create:
        make_engine('postgresql://localhost/example')
        create.assert_called_once_with('postgresql://localhost/example')


def test_request_sessions_rollback_and_close(tmp_path):
    app = create_app(storage='orm', database_url=f"sqlite:///{tmp_path / 'sessions.db'}")
    Base.metadata.create_all(app.state.engine)
    sessions = []

    @app.post('/probe/{fail}')
    def probe(fail: bool, db=Depends(get_db)):
        sessions.append(db)
        db.add(User(email='fail@example.com' if fail else 'ok@example.com', password_hash='hash'))
        db.flush()
        if fail:
            raise RuntimeError('failure')
        db.commit()
        return {'ok': True}

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post('/probe/true').status_code == 500
        assert client.post('/probe/false').status_code == 200
    assert sessions[0] is not sessions[1]
    assert all(not s.in_transaction() and not s.identity_map for s in sessions)
    with app.state.session_factory() as db:
        assert list(db.scalars(select(User.email))) == ['ok@example.com']
    app.state.engine.dispose()
