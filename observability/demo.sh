#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Never inherit normal Compose resource names or cloud telemetry settings.
export COMPOSE_PROJECT_NAME=gradematch-obs-demo
export OBS_OTLP_BIND_ADDRESS=127.0.0.1
export OBS_4318_PORT=14318 OBS_13133_PORT=13134 OBS_9090_PORT=19090
export OBS_3100_PORT=13100 OBS_3200_PORT=13200 OBS_3000_PORT=13000
export DEMO_DEV_VERSION=${DEMO_DEV_VERSION:-$(git rev-parse --short=7 HEAD)}
export DEMO_PROD_VERSION=${DEMO_PROD_VERSION:-$(git rev-parse --short=7 HEAD^)}
for version in "$DEMO_DEV_VERSION" "$DEMO_PROD_VERSION"; do
    printf '%s\n' "$version" | LC_ALL=C grep -Eq '^[0-9a-f]{7}$' || {
        echo 'Demo versions must be seven lowercase hexadecimal characters' >&2; exit 1;
    }
done
compose() {
    docker compose -p gradematch-obs-demo -f observability/docker-compose.yaml -f observability/demo-compose.yaml "$@"
}
case "${1:-up}" in
    down) compose down -v --remove-orphans ;;
    up)
        compose up -d --build --wait --wait-timeout 240
        python3 observability/demo.py
        ;;
    *) echo 'Usage: observability/demo.sh [up|down]' >&2; exit 1 ;;
esac
