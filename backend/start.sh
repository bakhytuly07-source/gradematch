#!/bin/sh
set -eu

# Render supplies the actual deployment SHA, including manual older-commit deploys.
if [ -n "${RENDER_GIT_COMMIT:-}" ]; then
    APP_VERSION=$(printf '%.7s' "$RENDER_GIT_COMMIT")
    export APP_VERSION
fi

python -m app.readiness
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8091}"
