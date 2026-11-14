# Optional telemetry

Telemetry is off unless `OTEL_EXPORTER_OTLP_ENDPOINT` is nonempty. Set it to an
OTLP HTTP Collector base URL (for example `http://localhost:4318`). The app sends
protobuf requests to `/v1/traces`, `/v1/metrics` and `/v1/logs`. No Render variables
are newly required. Identity is `service.name=gradematch`,
`deployment.environment=$DEPLOYMENT_ENVIRONMENT` (default `local`) and
`service.version=$APP_VERSION` (default `dev`). Docker accepts
`--build-arg APP_VERSION=...`.

Providers belong to an app, are never installed globally, use bounded queues,
one-second HTTP export timeouts and shut down with app lifespan. Request spans
include method, route template and status only. SQLAlchemy engine-local spans
include database dialect only, without SQL, parameters or exception events.
An application completion log and HTTP request counter exercise all three
signals without capturing body, headers, query string, credentials or images.
Normal Python logging remains available when telemetry is disabled.

Run `cd backend && uv run pytest tests/test_telemetry.py -q` for an actual local
OTLP HTTP receiver that decodes trace/metric/log protobufs, runs an authenticated
ORM register/generate/save journey, checks identity and scans exports for private
values. It also tests an unreachable endpoint and disabled worker behavior.
