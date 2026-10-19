import os
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


DEFAULT_URL = f"sqlite:///{Path(__file__).resolve().parents[1] / 'gradematch.db'}"


def make_engine(url: str):
    return create_engine(url)


engine = make_engine(os.getenv("DATABASE_URL", DEFAULT_URL))
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db(request: Request):
    # In-memory applications never instantiate a database session or connection.
    if request.app.state.memory is not None:
        yield None
        return
    with SessionLocal() as session:
        yield session
