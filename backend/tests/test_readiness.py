import subprocess
from types import SimpleNamespace

import pytest

from app import readiness


@pytest.mark.parametrize("outcomes,elapsed,success", [
    ([0], 0, True),
    ([1, 1, 0], 2, True),
    ([1] * 30, 30, False),
    (["hang"] * 30, 30, False),
    ([1] * 29 + [0], 29, True),
])
def test_readiness_retry_window(monkeypatch, capsys, outcomes, elapsed, success):
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    def run(argv, **kwargs):
        assert argv == [readiness.sys.executable, "-m", "app.readiness", "--connect"]
        assert 0 < kwargs["timeout"] <= min(1, 30 - now[0])
        assert kwargs["stdout"] == kwargs["stderr"] == subprocess.DEVNULL
        outcome = outcomes.pop(0)
        if outcome == "hang":
            now[0] += kwargs["timeout"]
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        return SimpleNamespace(returncode=outcome)

    monkeypatch.setattr(readiness.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(readiness.time, "sleep", sleep)
    monkeypatch.setattr(readiness.subprocess, "run", run)
    assert readiness.wait_for_database() is success
    assert now[0] == elapsed
    assert all(0 <= delay <= 1 for delay in sleeps)
    captured = capsys.readouterr()
    if success:
        assert "Database ready" in captured.out
    else:
        assert "Database readiness timeout after 30 seconds" in captured.err
