"""Database URL configuration without application initialization."""

import os
from pathlib import Path

DEFAULT_URL = f"sqlite:///{Path(__file__).resolve().parents[1] / 'gradematch.db'}"


def normalize_database_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def database_url():
    return normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_URL))

