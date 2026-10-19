import os
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


DEFAULT_URL = f"sqlite:///{Path(__file__).resolve().parents[1] / 'gradematch.db'}"


def database_url():
    return os.getenv("DATABASE_URL", DEFAULT_URL)


def make_engine(url: str | None = None):
    return create_engine(database_url() if url is None else url)


engine = make_engine()
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db(request: Request):
    # In-memory applications never instantiate a database session or connection.
    if request.app.state.memory is not None:
        yield None
        return
    with request.app.state.session_factory() as session:
        try:
            yield session
        except BaseException:
            session.rollback()
            raise
