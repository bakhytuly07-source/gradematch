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

## Manual production promotion (#139)

`.github/workflows/promote-production.yml` is dispatch-only. Configure the GitHub
`production` environment with any required reviewers and restrict deployment
branches to `main`. Its job grants only `actions: read` (exact-SHA CI inspection)
and `contents: write` (atomic release tag creation). The single job concurrency
group `production-promotion`, with cancellation disabled, serializes production
promotions. GitHub allows one running and one pending job per group; a newer
pending job can replace an older pending job, but does not cancel the running
promotion. Dispatch confirmations on `main` only; the runner is checked out from
`main` and the deployed commit is independently frozen from Render dev metadata.

Required secrets (repository or `production` environment): `RENDER_API_KEY`,
`RENDER_DEV_SERVICE_ID`, `RENDER_PROD_DEPLOY_HOOK_URL`. The API key needs read
access to deploy metadata for both services. Set repository/environment variables
`DEV_URL=https://gradematch-web.onrender.com`,
`PROD_URL=https://gradematch-prod.onrender.com`, and `RENDER_PROD_SERVICE_ID` to the
actual non-secret Render `srv-…` production service ID. Verify the actual URLs
and ID against Render before enabling promotion. The first two repository
variables exist; the production service ID was absent at implementation time.
No service identity is inferred from its name. Missing configuration fails
before the hook. The hook URL must target `https://api.render.com` with its
existing authentication query and no preconfigured `ref`.

The standard-library runner reads Render's official
[deployment-list response](https://api-docs.render.com/reference/list-deploys)
(`deployWithCursor` array, `deploy.commit.id`, `deploy.status`; pagination is
followed). Exactly one `live` dev deployment is required. Newer queued/building
or failed entries cannot replace it. CI is read by full SHA from `ci.yml`, with
the latest updated run/attempt required successful, including all three jobs.
Dev `/docs` must return the Swagger application before deploying. Public HTTP
requests refuse redirects; wake-up retries are bounded to two minutes for dev.

The [documented hook behavior](https://render.com/docs/deploy-hooks) preserves
existing query parameters and appends URL-encoded `ref=<full SHA>`. HTTP 200
supplies `deploy.id`; HTTP 202 requires discovery of a new matching hook deploy,
excluding all pre-hook deploy IDs. Metadata must identify the frozen SHA as live,
then the actual prod Swagger `/docs` must be healthy, within 600 seconds measured
from hook invocation, including hook time. Per-request timeouts never exceed
the remaining deadline. No previous healthy deployment can satisfy this gate.
Smoke requests then require `/`, `/login`, `/docs` 200 and `/api/auth/me` 401 with
the existing JSON error shape. Only then an atomic GitHub ref creation publishes
`prod-YYYYMMDD-HHMMSS-<first seven SHA characters>` in UTC. Existing refs fail;
tags are never overwritten. No tag is created on earlier failures.

A false confirmation exits with zero metadata/deployment calls and no tag.
Summaries report outcome, full SHA, public URLs, UTC timestamps, elapsed time,
note, CI URL, deployment ID, hook-call count and successful tag. Untrusted note
characters are numeric HTML entities, preventing Markdown/HTML/mention execution;
secrets and raw HTTP error bodies are suppressed. A failure after the hook can
leave the new production deployment live; the workflow does not roll back.

Isolated checks: `python3 -m unittest discover -s scripts/tests -v`. They cover
false confirmation, missing/pending/failed CI, unhealthy dev, hook HTTP error,
wrong prod SHA, the simulated full 600-second deadline, queued-deploy matching,
smoke failure, frozen SHA/query preservation and untrusted summary text. Real
rejected/successful dispatch, Render event, release tag and concurrent-confirmation
evidence are intentionally left to QA; implementation never invokes the live hook.

Implementation verification on 2026-11-15: promotion isolated checks **7 passed**;
workflow parsed with existing PyYAML and dispatch/input/permission/concurrency
invariants passed; backend **224 passed, 1 opt-in PostgreSQL test skipped**;
frontend **52 passed**; `make integration` **10 passed**; `make e2e` guest,
Library and Studio-session scenarios plus **30 Playwright tests passed** (1.1m).
Backend required sandbox escalation for its loopback OTLP receiver; Docker
checks required local Docker socket access. Existing product preview timings
above 300ms remain visible in the unchanged E2E suite. `openapi.yaml` is unchanged,
no dependency was added, and no existing CI/test assertion was changed. Actual
dev `/docs` availability and all live-promotion evidence remain QA checks.

QA correction (2026-11-15): urllib raises `HTTPError` for the expected auth 401.
The promotion transport must retain its JSON body for smoke contract validation,
rather than replacing every error response body with empty bytes. Error bodies
are now read only into memory with a 1 MiB limit and never logged. A regression
uses a real loopback HTTP server and the real urllib transport: valid 401 JSON
passes all smoke checks; an empty error message fails. All **8 isolated promotion
tests passed** after this correction. Earlier live attempts reached production
but failed this smoke check and created no tag; they are not successful releases.
The application/OpenAPI and existing CI workflow are unchanged by the fix.

Promotion summary evidence: the runner copies its own `GITHUB_STEP_SUMMARY` file
byte-for-byte to `$RUNNER_TEMP/promotion-summary.md` immediately after writing
its sanitized summary, on success or handled failure. An `always()` artifact
step uploads only that explicit file as
`promotion-summary-<run ID>-<attempt>` with 30-day retention. This supports
independent verification when GitHub's summary viewer is inaccessible. It does
not upload environment variables, response bodies or the working directory;
it preserves the promotion step's failure status. An unavailable summary is
reported as a missing artifact, never as successful verification. The summary
regression checks byte equality between the written summary and artifact file.
