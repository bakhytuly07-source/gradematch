#!/usr/bin/env bash
set -euo pipefail
gh label create observability --color 1D76DB 2>/dev/null || true
gh api repos/:owner/:repo/milestones -f title="M9 Observability" >/dev/null 2>&1 || true
mk() { gh issue create --label observability --milestone "M9 Observability" --title "$1" --body "Goal: $2

Description: $3"; }
mk "OpenTelemetry in the backend" "The backend sends traces, metrics and logs over OTLP with service name, environment and deployed version." "Instrument FastAPI, SQLAlchemy and logging. Settings come from environment variables; without an endpoint telemetry is off."
mk "Application metrics" "Counters and a latency histogram describe how GradeMatch is used and where it fails." "Styles generated, generate failures by reason, looks saved, users registered, LUT render duration, each with environment and version."
mk "Observability stack with Docker Compose" "One command starts a local observability stack separate from the app stack." "observability/ with OpenTelemetry Collector, Prometheus, Loki, Tempo and Grafana, a README and make targets."
mk "Connect the app to the observability stack" "Telemetry from the running app appears in Prometheus, Loki and Tempo." "A manual scenario (register, generate a style, save a look) produces metrics, logs and traces visible in Grafana."
mk "Grafana dashboard as code" "A dashboard loads automatically and can be filtered by environment and version." "Panels for the application metrics and request rate; dashboard JSON and provisioning files are committed."
mk "Alert on repeated generate failures" "An alert fires when style generation keeps failing and tells the responder where to look." "Prometheus rule with a threshold and duration that reflect user impact, labels for service, environment, version and owner, and the dashboard link."
mk "On-call engineer: alert poller and headless agent" "When an alert fires, an agent session starts, investigates and proposes a fix." "on-call-engineer/ script polls the alert API every minute, starts a headless coding agent once per alert on a separate branch without pushing, saves the log, has a dry-run mode."
mk "Fault injection drill" "A realistic bug causes the alert and the on-call agent responds." "Introduce the bug on a throwaway branch only, never on main (Render deploys main), trigger it, record the alert and the agent log."
mk "Observability documentation and evidence" "A reader can run the stack and see the evidence." "docs/observability.md with architecture, how to run, metric list, alert definition, on-call flow and screenshots."
