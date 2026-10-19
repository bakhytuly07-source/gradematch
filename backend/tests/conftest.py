from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import get_db, make_engine
from app.main import create_app


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = make_engine(url)
    # Run the actual migrations, rather than create_all: tests verify deployment schema too.
    import app.database as module
    monkeypatch.setattr(module, "engine", engine)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(database):
    app = create_app(storage="orm")
    def override_db():
        with database() as db:
            yield db
    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def memory_app():
    return create_app()


@pytest.fixture
def memory_client(memory_app):
    with TestClient(memory_app, raise_server_exceptions=False) as client:
        yield client
