"""Opt-in integration journey; TEST_DATABASE_URL must name an empty disposable DB."""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth import token_digest
from app.database import make_engine
from app.main import create_app
from app.models import AccessToken, Look, User
from test_api import SETTINGS, assert_schema


@pytest.fixture
def postgres(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("Set TEST_DATABASE_URL to an empty disposable PostgreSQL database")
    if make_url(url).drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg://")
    engine = make_engine(url)
    try:
        # Refuse existing schemas/data rather than destroying an unrelated database.
        if inspect(engine).get_table_names():
            pytest.fail("TEST_DATABASE_URL must target an empty disposable database")
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")
        try:
            assert set(inspect(engine).get_table_names()) == {
                "users", "access_tokens", "looks", "alembic_version"}
            with engine.connect() as connection:
                assert MigrationContext.configure(connection).get_current_heads() == (
                    ScriptDirectory.from_config(config).get_current_head(),)
            command.upgrade(config, "head")
            yield url, engine
        finally:
            command.downgrade(config, "base")
            # Alembic retains its empty version table after downgrade.
            from sqlalchemy import MetaData, Table
            Table("alembic_version", MetaData(), autoload_with=engine).drop(engine)
    finally:
        engine.dispose()


def test_postgres_migrations_and_committed_library_journey(postgres):
    url, engine = postgres
    app = create_app(storage="orm", database_url=url)
    assert app.state.memory is None
    assert app.state.engine.url == engine.url
    try:
        with TestClient(app) as client:
            payload = {**SETTINGS, "name": "PostgreSQL look", "thumbnail": ""}
            assert client.post("/api/looks", json=payload).status_code == 401
            with Session(engine) as db:
                assert list(db.scalars(select(Look))) == []
            auth = assert_schema(client.post("/api/auth/register", json={
                "email": "postgres@example.com", "password": "password123"}), "AuthResult", 201)
            assert auth["token_type"] == "bearer"
            headers = {"Authorization": "Bearer " + auth["access_token"]}
            saved = assert_schema(client.post("/api/looks", json=payload, headers=headers), "Look", 201)
            response = client.get("/api/looks", headers=headers)
            assert response.status_code == 200
            assert response.json() == [saved]
            assert saved["style_params"] == SETTINGS["styleParams"]
            assert saved["adjustments"] == SETTINGS["adjustments"]
        with Session(engine) as db:
            user = db.scalars(select(User)).one()
            token = db.scalars(select(AccessToken)).one()
            look = db.scalars(select(Look)).one()
            assert user.id == auth["user"]["id"]
            assert user.email == "postgres@example.com"
            assert token.token_hash == token_digest(auth["access_token"])
            assert token.user_id == look.user_id == user.id
            assert db.get(User, look.user_id) is user
            assert look.id == saved["id"]
            assert look.style_params == SETTINGS["styleParams"]
            assert look.adjustments == SETTINGS["adjustments"]
    finally:
        app.state.engine.dispose()
