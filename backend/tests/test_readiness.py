import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from app import readiness


def simulate(monkeypatch, outcomes, budget=None):
    now, attempts, sleeps = [0.0], [], []
    if budget is None:
        monkeypatch.delenv('READINESS_TIMEOUT', raising=False)
    else:
        monkeypatch.setenv('READINESS_TIMEOUT', str(budget))

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    def run(argv, **kwargs):
        attempts.append((now[0], kwargs['timeout']))
        assert argv == [sys.executable, '-m', 'app.readiness', '--connect']
        assert kwargs['capture_output'] and kwargs['text']
        duration, status, reason = next(outcomes)
        now[0] += min(duration, kwargs['timeout'])
        if duration > kwargs['timeout']:
            raise subprocess.TimeoutExpired(argv, kwargs['timeout'], stderr='never print raw timeout output')
        return SimpleNamespace(returncode=status, stderr=reason, stdout='')

    monkeypatch.setattr(readiness.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(readiness.time, 'sleep', sleep)
    monkeypatch.setattr(readiness.subprocess, 'run', run)
    return now, attempts, sleeps


@pytest.mark.parametrize('budget,total', [(None, 120), ('25', 25)])
def test_deadline_and_retry_rules(monkeypatch, capsys, budget, total):
    now, attempts, sleeps = simulate(monkeypatch, iter([(50, 1, '')] * 20), budget)
    assert not readiness.wait_for_database()
    assert now[0] == total
    assert all(start < total and timeout == min(10, total-start) for start, timeout in attempts)
    assert all(0 < delay <= 2 for delay in sleeps)
    assert 'TimeoutExpired' in capsys.readouterr().err


def test_three_second_connection_succeeds(monkeypatch):
    now, attempts, sleeps = simulate(monkeypatch, iter([(3, 0, '')]))
    assert readiness.wait_for_database()
    assert now[0] == 3 and attempts == [(0, 10)] and sleeps == []


def test_failures_wait_two_seconds_then_success(monkeypatch):
    now, attempts, sleeps = simulate(monkeypatch, iter([(0, 1, 'OperationalError: refused'), (3, 0, '')]))
    assert readiness.wait_for_database()
    assert attempts == [(0, 10), (2, 10)] and sleeps == [2] and now[0] == 5


def test_final_delay_is_capped(monkeypatch):
    now, attempts, sleeps = simulate(monkeypatch, iter([(0, 1, 'ConnectionError: refused')]), 1)
    assert not readiness.wait_for_database()
    assert now[0] == 1 and attempts == [(0, 1)] and sleeps == [1]


@pytest.mark.parametrize('value', ['', 'bad secret', '0', '-1', 'nan', 'inf'])
def test_invalid_configuration(monkeypatch, capsys, value):
    monkeypatch.setenv('READINESS_TIMEOUT', value)
    monkeypatch.setattr(readiness.subprocess, 'run', lambda *a, **kw: pytest.fail('must not connect'))
    assert not readiness.wait_for_database()
    captured = capsys.readouterr()
    assert 'ConfigurationError' in captured.err and 'bad secret' not in captured.err


def test_credentials_are_redacted_in_attempt_and_final(monkeypatch, capsys):
    url = 'postgresql://user:recognizable-secret@db:5432/example'
    monkeypatch.setenv('DATABASE_URL', url)
    reason = f'OperationalError: refused {url}\npassword recognizable-secret'
    simulate(monkeypatch, iter([(0, 1, reason)]), 1)
    assert not readiness.wait_for_database()
    captured = capsys.readouterr()
    assert url not in captured.out + captured.err
    assert 'recognizable-secret' not in captured.out + captured.err
    assert len(captured.err.splitlines()) == 2
    assert captured.err.count('OperationalError: refused') == 2


def test_connect_sanitizes_exception_and_disposes(monkeypatch, capsys):
    import sqlalchemy
    disposed = []
    class BrokenEngine:
        def connect(self):
            raise RuntimeError('refused postgresql://user:recognizable-secret@db/test recognizable-secret')
        def dispose(self):
            disposed.append(True)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:recognizable-secret@db/test')
    monkeypatch.setattr(sqlalchemy, 'create_engine', lambda url: BrokenEngine())
    assert readiness.connect() == 1
    output = capsys.readouterr()
    assert disposed == [True]
    assert output.err.startswith('RuntimeError: refused')
    assert 'recognizable-secret' not in output.out + output.err
    assert len(output.err.splitlines()) == 1


def test_connection_import_isolation():
    script = '''
import sys
from app.readiness import connect
assert connect() == 0
assert not any(name.split('.')[0] in {'fastapi', 'starlette'} or name in {'app.main', 'app.database'} for name in sys.modules)
'''
    result = subprocess.run([sys.executable, '-c', script], env={**os.environ, 'DATABASE_URL': 'sqlite://'}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_success_at_deadline_does_not_start_migrations(monkeypatch, capsys):
    now, attempts, sleeps = simulate(monkeypatch, iter([(1, 0, '')]), 1)
    assert not readiness.wait_for_database()
    captured = capsys.readouterr()
    assert 'Database ready;' not in captured.out
    assert 'completed after readiness deadline' in captured.err
    assert sleeps == [] and now[0] == 1


def test_timeout_discards_raw_child_errors(monkeypatch, capsys):
    simulate(monkeypatch, iter([(3, 1, '')]), 1)
    assert not readiness.wait_for_database()
    captured = capsys.readouterr()
    assert 'never print raw timeout output' not in captured.out + captured.err
    assert captured.err.count('TimeoutExpired:') == 2


def test_encoded_password_is_also_redacted(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:secret%40value@db/test')
    assert readiness.sanitize_reason('RuntimeError: secret%40value secret@value') == 'RuntimeError: [redacted] [redacted]'
