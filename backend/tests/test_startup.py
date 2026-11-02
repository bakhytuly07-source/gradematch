from fastapi.testclient import TestClient

from app.main import app


def test_application_lifecycle():
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 200


def test_entrypoint_migration_gate_and_port(tmp_path):
    import os
    from pathlib import Path
    import subprocess

    calls = tmp_path / 'calls'
    for name, body in {
        'alembic': 'echo "alembic $*" >> "$CALLS"; exit "${MIGRATION_EXIT:-0}"',
        'uvicorn': 'echo "uvicorn $*" >> "$CALLS"',
    }.items():
        command = tmp_path / name
        command.write_text('#!/bin/sh\n' + body + '\n')
        command.chmod(0o755)
    env = {**os.environ, 'PATH': str(tmp_path) + ':' + os.environ['PATH'], 'CALLS': str(calls)}
    env.pop('PORT', None)
    script = Path(__file__).resolve().parents[1] / 'start.sh'
    for port in [None, '8092']:
        if port:
            env['PORT'] = port
        result = subprocess.run(['/bin/sh', str(script)], env=env)
        assert result.returncode == 0
        assert calls.read_text().splitlines() == [
            'alembic upgrade head', f'uvicorn app.main:app --host 0.0.0.0 --port {port or "8091"}']
        calls.unlink()
    result = subprocess.run(['/bin/sh', str(script)], env={**env, 'MIGRATION_EXIT': '7'})
    assert result.returncode == 7
    assert calls.read_text().splitlines() == ['alembic upgrade head']
