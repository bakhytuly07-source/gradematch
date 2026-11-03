"""Bound database startup attempts and emit credential-free diagnostics."""

import math
import os
import re
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit


def sanitize_reason(reason: str) -> str:
    url = os.getenv("DATABASE_URL", "")
    secrets = [url]
    if url:
        try:
            password = urlsplit(url).password
            if password:
                secrets.extend([password, unquote(password)])
        except ValueError:
            pass
    for secret in sorted(filter(None, secrets), key=len, reverse=True):
        reason = reason.replace(secret, "[redacted]")
    reason = re.sub(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s\"'<>]+", "[redacted URL]", reason)
    return " ".join(reason.split())[:400]


def connect() -> int:
    # Keep web application/framework initialization out of this subprocess.
    try:
        from app.database_url import database_url
        from sqlalchemy import create_engine

        engine = create_engine(database_url())
        try:
            with engine.connect():
                pass
        finally:
            engine.dispose()
        return 0
    except Exception as exc:
        print(sanitize_reason(f"{type(exc).__name__}: {exc}"), file=sys.stderr, flush=True)
        return 1


def wait_for_database() -> bool:
    try:
        budget = float(os.getenv("READINESS_TIMEOUT", "120"))
        if not math.isfinite(budget) or budget <= 0:
            raise ValueError
    except ValueError:
        print("ConfigurationError: READINESS_TIMEOUT must be a positive finite number of seconds.",
              file=sys.stderr, flush=True)
        return False
    deadline = time.monotonic() + budget
    print(f"Waiting for database readiness ({budget:g}-second timeout).", flush=True)
    last_reason = "TimeoutExpired: total readiness deadline reached"
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app.readiness", "--connect"],
                timeout=min(10, remaining), capture_output=True, text=True,
            )
            if result.returncode == 0 and time.monotonic() < deadline:
                print("Database ready; starting migrations.", flush=True)
                return True
            if result.returncode == 0:
                last_reason = "TimeoutExpired: connection completed after readiness deadline"
            else:
                last_reason = sanitize_reason(result.stderr or result.stdout or
                                              f"ConnectionError: connection process exited {result.returncode}")
        except subprocess.TimeoutExpired:
            last_reason = "TimeoutExpired: connection attempt exceeded its allotted readiness budget"
        print(f"Database readiness attempt failed: {last_reason}", file=sys.stderr, flush=True)
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(2, remaining))
    print(f"Database readiness timeout after {budget:g} seconds; startup aborted. Last failure: {last_reason}",
          file=sys.stderr, flush=True)
    return False


if __name__ == "__main__":
    sys.exit(connect() if sys.argv[1:] == ["--connect"] else
             (0 if wait_for_database() else 1))
