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

## Business metrics

OTLP counter instrument names are `gradematch_styles_generated`,
`gradematch_generate_failures`, `gradematch_looks_saved` and
`gradematch_users_registered`. A standard Prometheus exporter adds `_total`.
The histogram is `gradematch_lut_render_seconds` (`_bucket`, `_sum`, `_count`).
Every observation carries `environment` and `version` labels from the same
configuration as resource identity; no user/filename/exception values are labels.
Success counters run only after successful processing or database commit.

Generate failure reasons form a finite vocabulary: `invalid_request` for missing
or malformed multipart uploads, `too_large` for byte limits, `invalid_image` for
unsupported formats or corrupt image decoding, and `processing_error` for
unexpected processing exceptions. Each failed generate handler records once.
The render histogram times only successful LUT construction plus conversion to
its response dictionary/list, excluding request validation, response JSON
serialization and network I/O. Explicit second boundaries are
0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5 (+Inf).

`uv run pytest tests/test_metrics.py -q` exercises in-memory readings before and
after API operations, failed database commits, all failure categories and real
Prometheus text export names/labels using a private registry. The Prometheus
exporter is a dev-only dependency; runtime exports through OTLP and exposes no
new public endpoint. Telemetry stays disabled without an OTLP endpoint.
