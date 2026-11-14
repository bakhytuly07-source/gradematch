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
