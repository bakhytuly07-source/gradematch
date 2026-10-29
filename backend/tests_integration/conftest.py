"""Shared, bounded readiness gate for the external Compose stack."""
import os
from pathlib import Path
import subprocess
import time

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8091").rstrip("/")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def compose(*args, timeout=30):
    result = subprocess.run(
        ["docker", "compose", *args], cwd=ROOT, capture_output=True,
        text=True, timeout=timeout,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout


def pytest_sessionstart(session):
    # One gate before any scenario, including when selecting an individual test.
    deadline = time.monotonic() + 9
    pending = [BASE_URL + "/docs", FRONTEND_URL + "/", FRONTEND_URL + "/login"]
    diagnostic = ""
    with httpx.Client(timeout=1, trust_env=False) as probe:
        while pending and time.monotonic() < deadline:
            url = pending[0]
            try:
                response = probe.get(url, timeout=min(1, deadline - time.monotonic()))
                diagnostic = f"{url}: HTTP {response.status_code}"
                if response.status_code == 200:
                    pending.pop(0)
                    continue
            except httpx.HTTPError as exc:
                diagnostic = f"{url}: {exc}"
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
    if pending:
        pytest.exit(
            f"Integration stack unavailable ({diagnostic}). Run `make up` from the repository root, "
            "then retry; check BASE_URL and FRONTEND_URL overrides.", returncode=1,
        )


@pytest.fixture
def api():
    with httpx.Client(base_url=BASE_URL, timeout=30, trust_env=False) as client:
        yield client


@pytest.fixture
def frontend():
    with httpx.Client(base_url=FRONTEND_URL, timeout=5, trust_env=False) as client:
        yield client
