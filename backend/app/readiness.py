"""Bound startup connection attempts without printing connection exceptions."""

import subprocess
import sys
import time


def wait_for_database() -> bool:
    deadline = time.monotonic() + 30
    print("Waiting for database readiness (30-second timeout).", flush=True)
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            # Isolate driver/DNS connection hangs; no credentials in argv or logs.
            result = subprocess.run(
                [sys.executable, "-m", "app.readiness", "--connect"],
                timeout=min(1, remaining),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0 and time.monotonic() < deadline:
                print("Database ready; starting migrations.", flush=True)
                return True
        except subprocess.TimeoutExpired:
            pass
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    print("Database readiness timeout after 30 seconds; startup aborted.",
          file=sys.stderr, flush=True)
    return False


if __name__ == "__main__":
    if sys.argv[1:] == ["--connect"]:
        from app.database import engine

        try:
            with engine.connect():
                pass
        finally:
            engine.dispose()
    else:
        sys.exit(0 if wait_for_database() else 1)
