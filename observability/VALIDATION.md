# Engineer validation

## #130 (2026-11-14 UTC)

- `docker compose -f observability/docker-compose.yaml config --quiet`: exit 0.
- Rendered images: otel/opentelemetry-collector-contrib:0.123.0,
  prom/prometheus:v3.2.1, grafana/loki:3.4.2, grafana/tempo:2.7.2,
  grafana/grafana:11.6.0. First pull succeeded; no retry needed.
- `make obs-up`, `make obs-down`, `make obs-up`: exit 0; all five services
  running. Down left zero observability containers; existing gradematch app/db
  container IDs remained 658209bac000 / e56febdb65ad and healthy.
- `python3 observability/check.py`: all five readiness checks and all three
  provisioned datasource checks pass, before and after restart. Initial Loki and
  Tempo readiness 503s resolve during warmup. Tempo's Grafana 11.6 backend health
  API is unimplemented; its configured datasource proxy readiness is asserted.
- Backend `uv run pytest`: 222 passed, 1 skipped (optional PostgreSQL test),
  5 existing warnings, 17.54s. Requires local socket permission for OTLP tests;
  sandboxed attempt had 2 receiver bind errors, corrected by approved rerun.
- Frontend `npm test -- --run`: 12 files / 52 tests passed, 1.05s.

## #131 (2026-11-14 UTC)

Commands run from repository root:

```sh
OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 docker compose config --quiet
OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 docker compose up -d --build --wait app
# Also recreated to verify changing existing containers:
OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 docker compose up -d --force-recreate --wait app
python3 observability/smoke.py
```

App-container DNS resolved `host.docker.internal=192.168.65.254`; empty protobuf
POST to `http://host.docker.internal:4318/v1/traces` returned 200. Both default
Compose config and native-Linux example `OBS_OTLP_BIND_ADDRESS=172.17.0.1`
render successfully; the latter binds only Docker's private bridge address.
Actual runtime validation used Docker Desktop's Linux engine on macOS; a native
Linux host was unavailable. README gives the exact native-Linux gateway lookup,
bind and container connectivity command. No public OTLP listener was started.

Sanitized final smoke output (Grafana link omitted for readability):

```text
2026-11-14T07:01:06.007657+00:00 command: python3 observability/smoke.py
2026-11-14T07:01:06.213089+00:00 baseline POST /api/auth/register -> 201
2026-11-14T07:01:06.250524+00:00 baseline POST /api/generate -> 200 style_id=ff9005d530b8940d7495e182
2026-11-14T07:01:06.255871+00:00 baseline POST /api/looks -> 201 look_id=53d5a8fe-2485-4bb0-9934-e35d3f315a8d
2026-11-14T07:01:18.274734+00:00 metrics before={"looks_saved": 3.0, "styles_generated": 3.0, "users_registered": 3.0}
2026-11-14T07:01:18.473990+00:00 scenario POST /api/auth/register -> 201
2026-11-14T07:01:18.477182+00:00 scenario POST /api/generate -> 200 style_id=ff9005d530b8940d7495e182
2026-11-14T07:01:18.480459+00:00 scenario POST /api/looks -> 201 look_id=330a4a4b-373d-4065-bb72-d9739b86be7a
2026-11-14T07:01:26.519781+00:00 metrics after={"looks_saved": 4.0, "styles_generated": 4.0, "users_registered": 4.0}
2026-11-14T07:01:26.536185+00:00 Loki query={service_name="gradematch",deployment_environment="local",service_version="dev"} |= "API request completed" start=1794639678274786000 end=1794639686519798000 log_timestamp_ns=1794639678476149760 trace_id=ce0884d3a08f82512ea885a4ccc8b840
2026-11-14T07:01:26.536201+00:00 Tempo GET /api/traces/ce0884d3a08f82512ea885a4ccc8b840 -> 200; service=gradematch environment=local version=dev; span=POST /api/generate
2026-11-14T07:01:26.536241+00:00 PASS: metrics increment and log/trace IDs match
```

An earlier run at 06:56:41–06:56:51 UTC also showed all three counters 1 → 2,
with trace ID `1d6aa9c54e35f30e981dad180bf8aec2`. Browser verification confirmed:
all three sources appear in Connections → Data sources; Tempo's Test displays
“Successfully connected to Tempo data source.”; Loki's exact documented query
and absolute 06:56:40–06:57:00 UTC window return the generate completion log
with gradematch/local/dev identity; expanding it shows the same trace ID and
**Open trace** opens Tempo's `gradematch: POST /api/generate`, HTTP 200, 1.44ms.
The Grafana provisioning template escapes the dollar sign so the derived link
retains `${__value.raw}` at runtime.

Collector outage: `docker compose -f observability/docker-compose.yaml stop
collector`, then `curl --fail ... http://localhost:8091/docs` returned 200; the
Collector was restarted. `OTEL_EXPORTER_OTLP_ENDPOINT= docker compose up -d
--force-recreate --wait app` succeeded and the app-container environment
assertion printed `telemetry endpoint empty`.

With endpoint cleared:

- `make integration`: exit 0, 10 passed in 7.70s.
- `make e2e`: exit 0, guest/library/studio-session legacy journeys passed,
  30 Playwright specs passed in 1.0m. Existing diagnostic preview timings
  366–427ms exceed the 300ms product target but are not assertion failures.
- Backend `uv run pytest`: 222 passed, 1 optional PostgreSQL skip, 5 existing
  warnings in 17.71s. Focused real-OTLP correlation test: 5 passed in 3.33s,
  including default/custom identity, nonzero trace/span IDs and private-value
  exclusion.
- Frontend `npm test -- --run`: 12 files / 52 tests passed in 1.12s.

Completion logs previously lost request context before LoggingHandler created
its record. The narrow fix reinstates that context for the completion record;
regression assertions require every request trace ID to occur in the logs.
No endpoint/API-contract, dependency or Render changes. Telemetry remains off
by default and was restored off after the final smoke.

## Engineer #132 — 2026-11-14

No dependency, API, backend or Render changes. Existing Collector conversion
exports `gradematch_http_requests_total` with resource identity labels.
Dashboard API returned `provisioned=true`, UID `gradematch`, URL
`/d/gradematch/gradematch`; identical after actual obs-down/obs-up.

Live `dashboard_smoke.py` ran two baseline/scenario journeys, 15s apart:

- 07:18:42–07:18:59 UTC, local/dev: all six exact panel expressions returned
  positive values. Styles/saves/users/failures ~0.0203/s, HTTP 0.1960/s,
  p95 0.00975s; failure reason `invalid_request`.
- 07:19:44–07:20:03 UTC, qa/test-build: all six expressions returned positive
  values. Styles/saves/users/failures ~0.0198/s, HTTP 0.2751/s, p95 0.00975s.

Each request used only its selected environment/version; business selectors
match observation labels and HTTP selectors match the exported resource labels.
Browser showed selected local/dev and qa/test-build with all six panel legends;
qa/test-build Last 5 minutes displayed the second scenario's distinct 07:20
traffic, excluding the first 07:18 scenario. Stable dashboard remained visible
after restart. The nonexistent pair showed “No matching traffic” in all six panels, without errors.
Frontend: 12 files / 52 tests passed. Backend initially hit sandbox loopback
restrictions in two existing OTLP receiver tests; rerun with loopback permission passed: 222 passed, 1 optional PostgreSQL skip, 5 existing warnings in 17.73s.

## Engineer #133 — 2026-11-14

Pinned stack `prom/prometheus:v3.2.1` ran `promtool check rules` (one rule,
SUCCESS) and `promtool test rules` (SUCCESS). Fixtures prove below threshold
has no pending/firing alert; the threshold is pending at 5m, does not fire at
6m55s, fires at 7m after the complete 2m hold, and resolves at 10m. Four reasons
sum into local/dev; qa/test-build yields a separate alert. Required labels and
both exact dashboard annotations are checked by promtool.

Real `alert_smoke.py --environment qa --version test-build` queried the rule
API after Prometheus recreation. Baseline 422 at 07:22:53 UTC, 15s settling,
then one missing-upload 422 every 10s. Pending observed 07:23:38; firing
observed 07:25:38.585561 UTC. Sanitized `/api/v1/alerts` evidence:

```json
{
  "state": "firing",
  "activeAt": "2026-11-14T07:23:33.695879708Z",
  "labels": {
    "alertname": "GradeMatchGenerateFailures",
    "environment": "qa",
    "version": "test-build",
    "service": "gradematch",
    "owner": "gradematch-maintainers"
  },
  "annotations": {
    "summary": "Repeated GradeMatch generate failures in qa / test-build",
    "description": "At least five generate failures over five minutes, sustained for two minutes. All failure reasons count. See the local runbook observability/README.md.",
    "dashboard_url": "http://localhost:3000/d/gradematch/gradematch?var-environment=qa&var-version=test-build"
  },
  "value": "1.6212056047582273e+01"
}
```

Browser opened that dashboard with Environment `qa` / Version `test-build`,
all six panel legends and the failure series. Traffic stopped at 07:25:38 UTC;
resolution check follows below. No fault-injection branch or production-code
changes; no dependencies added. `check.py` passed all five readiness checks,
three provisioned healthy data sources, stable provisioned six-panel dashboard.
Compose config and Python compile checks passed.

App defaults restored before normal suites: container assertion printed
`telemetry off; environment=local; version=dev`. `make integration` passed
10 tests in 8.13s. Backend full suite already passed 222 tests (one optional
PostgreSQL skip, five existing warnings); frontend 52 tests passed. All changes
after those suites are local observability configuration/scripts/docs.

Telemetry-off `make e2e`: PASS guest/library/studio-session legacy journeys and
30 Playwright tests in 1.0m. Existing preview diagnostic timings 376–441ms exceed
the 300ms product target, without assertion failures; no related code changes.
A fresh disposable Grafana 11.6.0 container, with only committed provisioning
and dashboard mounts and an empty data directory, automatically returned the
provisioned six-panel `gradematch` dashboard via its API. No manual import or
upload was used; disposable container removed after verification.

Live resolution PASS at **07:29:59.556441 UTC**: no matching alert remained in
`/api/v1/alerts`, 261s after traffic stopped, within the 360s bound. App and DB
remain running, observability stack remains available for QA, telemetry remains
off in the normal app. Issues stay open for independent QA verification.
