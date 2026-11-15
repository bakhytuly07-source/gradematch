# Environments

## Environment and database setup (#137)

`gradematch-web` remains dev: its resource name, Docker configuration and
`gradematch-db` binding are preserved. `gradematch-prod` is a separate free
Frankfurt Docker service with automatic deployment disabled. Supply its
`DATABASE_URL` securely through Render using a **separate Neon PostgreSQL
database**. Never copy dev's connection string. The unchanged entrypoint waits
for the database and runs Alembic before serving requests.

Render allows [one active free PostgreSQL database per workspace](https://render.com/docs/free),
so prod uses Neon. Render's free database expires after 30 days; the **actual dev
expiry notice/date is waiting for owner dashboard evidence**, not calculated
from this document. Free web instances sleep after 15 idle minutes; review the
linked current limits before relying on this environment.

For an existing Blueprint, `sync: false` does **not** apply a new secret on
updates: manually enter prod's secret in its Environment page before deploying.
On first Blueprint creation Render prompts for it. See the
[environment-variable specification](https://render.com/docs/blueprint-spec#environment-variables).

Before sync, record dev's actual service ID, URL and database identity. Review
Blueprint changes to confirm the existing resources are retained, only prod is
added, and no database is replaced. After sync record both identities, actual
URLs, plans, regions, deploy SHAs/events and successful migrations. Actual dev
and prod URLs and IDs are **waiting for owner evidence**; names are not URLs.
Verify `/`, `/login`, `/docs` each return 200 on both actual URLs after wake-up.

Use two distinct disposable accounts: register on dev only, verify successful
dev login and prod authentication error without registration; repeat in reverse.
Save a synthetic look in each and verify it is absent from the other Library.
Record sanitized statuses and look identifiers; omit credentials, emails,
connection strings and tokens. This cloud isolation evidence remains waiting
for owner access.

## Complete Blueprint field audit

Checked **2026-11-15 (Asia/Almaty)** against the requested
[YAML specification](https://render.com/docs/yaml-spec), its current
[Blueprint reference](https://render.com/docs/blueprint-spec), and the official
[JSON Schema](https://render.com/schema/render.yaml.json). Each row covers every
occurrence of that path in the complete file. Links identify the relevant
specification section.

| Field | Value | Purpose / specification |
| --- | --- | --- |
| `services` | two entries | [Non-Postgres services](https://render.com/docs/blueprint-spec#root-level-fields) |
| `services[].type` | `web` both | [HTTP services](https://render.com/docs/blueprint-spec#service-fields) |
| `services[].name` | `gradematch-web`, `gradematch-prod` | Stable service identities, same reference |
| `services[].runtime` | `docker` both | Existing image build, same reference |
| `services[].dockerfilePath` | `./Dockerfile` both | Repository Dockerfile, same reference |
| `services[].dockerContext` | `.` both | Root build context, same reference |
| `services[].plan` | `free` both | Free compute, same reference |
| `services[].region` | `frankfurt` both | Frankfurt deployment, same reference |
| `services[].healthCheckPath` | `/docs` both | Existing HTTP health path, same reference |
| `services[0].autoDeployTrigger` | `checksPass` | Dev waits for CI; [service fields](https://render.com/docs/blueprint-spec#service-fields) |
| `services[1].autoDeployTrigger` | quoted `off` | Manual prod deployment; same reference. Quotes preserve the string under YAML 1.1 validators. |
| `services[].envVars` | lists | [Environment entries](https://render.com/docs/blueprint-spec#environment-variables) |
| `services[].envVars[].key` | `DATABASE_URL`, `DEPLOYMENT_ENVIRONMENT` | Backend configuration keys, same reference |
| dev `DATABASE_URL.fromDatabase` | object | Managed database binding, same reference |
| `fromDatabase.name` | `gradematch-db` | Preserves dev database, same reference |
| `fromDatabase.property` | `connectionString` | Supported private URL property, same reference |
| prod `DATABASE_URL.sync` | `false` | Secure manual secret entry, same reference |
| `DEPLOYMENT_ENVIRONMENT.value` | `dev`, `prod` | Distinct telemetry environments, same reference |
| `databases` | one entry | [Postgres resources](https://render.com/docs/blueprint-spec#postgres-fields) |
| `databases[].name` | `gradematch-db` | Existing database identity, same reference |
| `databases[].plan` | `free` | Existing free instance, same reference |
| `databases[].region` | `frankfurt` | Existing database region, same reference |

Official schema downloaded 2026-11-15; SHA-256
`6c6721a602ef6d368d5c9384c473cefaae99980e43dd4b1adcf8a2f258fc54f4`.
Validation used existing backend development dependencies PyYAML 6.0.3 and
jsonschema 4.26.0, `validator_for(schema).check_schema(schema)` then
`validator(schema).validate(yaml.safe_load(Path('../render.yaml').read_text()))`.
Output: `PASS render.yaml: official Render JSON Schema`.
This validates structure, not dashboard settings or successful deployment.

## Automatic dev CI gate (#138)

Dev uses `autoDeployTrigger: checksPass`; prod remains `off`. The existing
`CI` workflow runs independent `backend` and `frontend` jobs, then dependent
`stack`. Backend runs the full pytest suite; frontend runs TypeScript, tests and
build; stack runs `make integration` and `make e2e`. No job or assertion changed.

[Render CI integration](https://render.com/docs/deploys#integrating-with-ci)
waits for checks on the exact new commit. GitHub conclusions `success`, `neutral`
and `skipped` count as passed; zero checks or a failed check blocks automatic
deployment. Keep all three jobs enabled. Privileged manual deploys and hooks
are separate from this automatic gate. The promotion workflow's independent
CI validation belongs to #139 and is outside this change.

The complete field audit above and official schema validation were repeated on
2026-11-15 after adding `checksPass`: `PASS render.yaml: official Render JSON Schema`
(same schema SHA-256 and validator versions).

Waiting for owner dashboard evidence: “After CI Checks Pass” on the unchanged
dev service; successful commit SHA, CI run URL/conclusion and completion time,
then Render event for that same SHA with timezone; endpoint HTTP 200 results.
For an owner-controlled failed/pending/recovery experiment, retain the prior
live SHA, failed SHA/run, terminal completion time and observation interval,
Render event history showing no deploy for failed/pending SHA, then recovery
CI completion and subsequent matching deploy event. Do not manufacture a broken
main commit as part of this implementation. A green GitHub run alone does not
prove the deployment gate or live service identity.

## Telemetry identity and repeatable local demo (#140)

Render's [actual deployment commit](https://render.com/docs/environment-variables#render_git_commit)
`RENDER_GIT_COMMIT` takes precedence over build defaults: startup exports its first
seven characters as `APP_VERSION`, and telemetry resource/business identity uses
the same resolution. Thus manually deploying an older SHA identifies that older
SHA. Explicit local `APP_VERSION` remains supported; telemetry stays opt-in via
`OTEL_EXPORTER_OTLP_ENDPOINT`. Resources expose `deployment.environment` and
`service.version`; business instruments expose matching `environment`/`version`.
Cloud request log/trace/metric identity versus actual deployment metadata remains
waiting for owner evidence on both services.

Prerequisites: Docker Desktop/Engine with Compose v2 supporting `--wait`, Python
3 standard library, Git, available image registry access, and this checkout with
its existing JPEG fixture. No cloud credentials or additional packages required.
From repository root:

```sh
make obs-demo
# Optional distinct seven-character lowercase hex commit overrides:
DEMO_DEV_VERSION=4717cb7 DEMO_PROD_VERSION=a3ce833 make obs-demo
make obs-demo-down
```

Defaults derive dev from `git rev-parse --short=7 HEAD` and prod from `HEAD^`.
Overrides identify the supplied demonstration versions; both containers run the
current working-tree image, not separate historical builds. Dev uses
`http://localhost:18091`, prod `http://localhost:18092`, Grafana
`http://localhost:13000` (local-only demo login `admin` / `admin`). Prometheus is
`:19090`, Loki `:13100`, Tempo `:13200`, Collector OTLP `:14318`, Collector health
`:13134`; every published port binds loopback. Internal app ports are both 8091.

The fixed project `gradematch-obs-demo` owns its network, containers and named
observability volumes. Each app has an independent SQLite database in its own
container `/tmp/demo.db`; recreation resets only that app's synthetic accounts.
No uploaded image is stored. Cleanup removes only this project's containers,
network and volumes, preserving normal app/integration/E2E and observability
projects and all cloud services. The demo overrides inherited Compose project
and OTLP binding settings. A second invocation reuses resources safely, waits
for readiness and sends new synthetic traffic. Shutdown is explicit even after
a failed run (`make obs-demo-down`).

The sample sends register, generate, save-look, render-LUT and rejected missing
upload actions from each app twice, separated by scrapes. Credentials remain in
memory. It asserts all six real dashboard queries are populated, metrics carry
matching resource/business identity, Loki request logs correlate to Tempo traces,
and exact dev/prod/both environment/version selections return the intended
nonempty series. Grafana's Environment and Version filters support multiple
values and All; version options follow selected environments using regex
selectors. The script prints URLs and writes sanitized query evidence to
`/tmp/gradematch-obs-demo-evidence.json` (override `DEMO_EVIDENCE_PATH`).

See [observability runbook](observability.md). Saved local evidence is in
`docs/img/obs-demo-evidence.json` and `obs-demo-dev.png`, `obs-demo-prod.png`,
`obs-demo-both.png`. These demonstrate local synthetic instances, not a cloud
deployment or production promotion.

## Local implementation verification (2026-11-15)

- Backend `UV_CACHE_DIR=/tmp/gradematch-uv-cache uv run pytest`: **224 passed,
  1 skipped** (opt-in PostgreSQL journey); includes actual older Render SHA
  precedence and local explicit-version regressions.
- Frontend `npm test -- --run`: **52 passed**, 12 files.
- `make integration`: **10 passed**, unchanged scenarios/assertions.
- `make e2e`: **PASS** guest, Library and Studio session scenarios plus **30
  Playwright tests** (1.2m), unchanged assertions. Existing preview timing
  observations above the product target remain reported by the suite.
- `make obs-demo`: PASS at 10:34:46 UTC; second invocation PASS at
  10:36:12 UTC. Supplied/default identities were dev `4717cb7`, prod `a3ce833`.
  Actual metrics, correlated request logs/traces and dev/prod/both filters are
  recorded in `docs/img/obs-demo-evidence.json`; populated Grafana screenshots
  show each selection. No cloud identity is claimed by these local results.
- `make obs-demo-down`: all demo containers and named volumes removed. Normal
  Compose container IDs before/after were identical; its `/docs` returned 200
  while the unchanged E2E suite continued running.
- `git diff -- openapi.yaml`: empty. No dependency added or assertion weakened.

Existing dev deployment, Blueprint sync/identities, Neon migrations, account/look
isolation, CI-gate event experiment and cloud telemetry matching actual deployed
SHAs remain **waiting for owner evidence**. These are required acceptance
criteria and must be verified before QA closes their issues.
