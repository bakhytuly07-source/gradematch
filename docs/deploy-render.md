# Deploy GradeMatch on Render

The root `render.yaml` creates one free Docker web service (`gradematch-web`)
and one free PostgreSQL database (`gradematch-db`), both in **Frankfurt**
(`frankfurt`). The existing Dockerfile builds the frontend and serves it with
the API on one origin. Reuse its entrypoint; it waits for the database, runs
Alembic migrations, then binds Uvicorn to `0.0.0.0:$PORT`.

Deployment status: **not yet verified**. The available Render browser session
requires sign-in. No public URL, database expiry date, or live test result has
been recorded. Complete the evidence steps below before claiming #122 passes.

## Create the Blueprint

1. Sign in to the [Render Dashboard](https://dashboard.render.com). Connect
   GitHub if needed and grant access to `bakhytuly07-source/gradematch`.
2. Select **New > Blueprint**, find that repository and click **Connect**.
3. Choose branch **main**, set **Blueprint Path** to root `render.yaml`, and
   name the Blueprint **gradematch**. Leave the repository root unchanged.
4. Review Render's validation result and proposed resources before creation.
   Confirm exactly one Docker web service and one PostgreSQL database, each
   **Free**, each **Frankfurt**. Resource names must be distinct. If Render
   reports existing resources or appends suffixes, inspect the proposed mapping
   before proceeding; do not attach to an unrelated database. A workspace can
   have only one active free PostgreSQL database.
5. Click **Deploy Blueprint**. Wait for the database to become available and
   the web service deployment to succeed. Open each resource's details to
   confirm its Free plan and Frankfurt region after creation.
6. On the web service's **Environment** page, confirm `DATABASE_URL` references
   the Blueprint database. Do not copy or reveal its resolved value. The
   `fromDatabase` / `connectionString` binding supplies the private URL; existing
   normalization in `backend/app/database.py` accepts both `postgres://` and
   `postgresql://` through psycopg. Do not add another normalizer or use SQLite.
7. Leave `CORS_ORIGINS` unset for same-origin hosting, leave `PORT` managed by
   Render, and keep Docker Command unset. No separate frontend service, build
   argument, start override, or pre-deploy migration command is required.
8. Open the web service's resource page and copy its public **HTTPS**
   `onrender.com` URL shown near the service name. Record the actual URL in the
   README and issue #122, rather than deriving it from the resource name.
9. Open the database's **Info** page and find its free-instance expiration
   notice/date. Write down the displayed expiry date as **YYYY-MM-DD** in the
   README and issue #122; do not estimate it from the date of this guide.

See [Blueprint setup](https://render.com/docs/infrastructure-as-code).

## Validate every Blueprint field

Checked against the requested [YAML specification](https://render.com/docs/yaml-spec)
and its current [Blueprint reference](https://render.com/docs/blueprint-spec).

| Field | Configured value and purpose |
| --- | --- |
| `services` | One non-Postgres service. |
| `services[].type` | `web`, a supported service type. |
| `services[].name` | `gradematch-web`, unique within this Blueprint. |
| `runtime` | `docker`, builds the existing image. |
| `dockerfilePath` | `./Dockerfile`, relative to repository root. |
| `dockerContext` | `.`, repository-root build context. |
| `services[].plan` | `free`, supported web compute plan. |
| `services[].region` | `frankfurt`, supported service region. |
| `healthCheckPath` | `/docs`, existing HTTP health endpoint. |
| `envVars` | List containing one environment binding. |
| `key` | `DATABASE_URL`, existing backend configuration key. |
| `fromDatabase` | Reference to the managed Postgres resource. |
| `fromDatabase.name` | `gradematch-db`, matches the database resource. |
| `property` | `connectionString`, private connection URL. `internalConnectionString` is not a supported Blueprint property. |
| `databases` | One PostgreSQL instance. |
| `databases[].name` | `gradematch-db`, unique resource name. |
| `databases[].plan` | `free`, supported database compute plan. |
| `databases[].region` | `frankfurt`, matches the web service. |

For reproducible offline structural validation, fetch Render's official schema
and use the project's existing development dependencies (no new dependency):

```sh
curl -fsSL https://render.com/schema/render.yaml.json -o /tmp/gradematch-render-schema.json
cd backend
uv run python - <<'PY'
import json
from pathlib import Path
import jsonschema
import yaml

schema = json.loads(Path('/tmp/gradematch-render-schema.json').read_text())
validator = jsonschema.validators.validator_for(schema)
validator.check_schema(schema)
validator(schema).validate(yaml.safe_load(Path('../render.yaml').read_text()))
print('PASS render.yaml: official Render JSON Schema')
PY
```

Record the command, validator version, schema download date/hash, and output in
#122. Structural validation does not prove account-specific resource availability
or successful deployment. Also retain Render's Blueprint review result from
step 4; if using Render CLI v2.7.0+ instead, run
`render blueprints validate render.yaml` and record its output.

Repository verification on 2026-11-03 (Asia/Almaty) used `jsonschema 4.26.0`
and `PyYAML 6.0.3` with that downloaded official schema. Output:
`PASS render.yaml: official Render JSON Schema`.
Schema SHA-256:
`8a3fb8da6b4f55fe686fbefa790e011d3dd7895f013f355953c572a21ab6494a`.
Render's authenticated Blueprint review is still pending.

## Logs, failures, and redeploys

Open the web service's **Events** page to select a build/deploy event and inspect
its build and deploy logs. Open **Logs** for runtime output. Look for database
readiness, Alembic migration completion, and Uvicorn startup before expecting
`/docs` health checks to succeed. Never include resolved database URLs in evidence.

Startup prints `Waiting for database readiness (30-second timeout).`, then
`Database ready; starting migrations.`. A readiness timeout aborts startup:
check database availability, matching region, and the `DATABASE_URL` reference.
A migration failure also stops startup; inspect the Alembic error before retrying.
For an unhealthy deploy, check its runtime logs, `/docs` health path and the
platform-provided port. Build failures belong in the selected event's build logs.

To redeploy while preserving accounts and looks, open the **existing web
service**, select **Manual Deploy > Deploy latest commit**, and wait for the
new event to become healthy. Keep the existing database and its binding. Record
the deploy event, commit, timestamp, and persistence evidence below.

For later `render.yaml` changes, commit and push to the Blueprint's linked
branch. Blueprint Auto Sync normally applies them automatically. If disabled,
open the Blueprint page and click **Manual Sync**, review the changes, and sync.
An app **Manual Deploy** rebuilds code; it does not replace Blueprint sync for
configuration updates. Confirm plans/regions and database identity after sync.

## Free-plan lifetime and wake-up

A free web service sleeps after **15 minutes** without inbound traffic. Its next
request can take **about a minute** to wake it. Warm `/docs` and wait for the
actual API response before running suites with short readiness timeouts.

The free PostgreSQL database **expires 30 days after creation**. Record its
actual expiry date from the database Info page. After expiry it is inaccessible;
Render provides a 14-day upgrade grace period before deleting the data. Plan
accordingly before storing anything that must survive the trial. See the current
[free-plan limits](https://render.com/docs/free).

## Live verification and evidence

After wake-up, use the actual service URL (without a trailing slash):

```sh
export PUBLIC_URL=https://your-actual-service.onrender.com
curl --fail --retry 12 --retry-delay 5 --retry-all-errors --max-time 120 "$PUBLIC_URL/docs" -o /dev/null
for route in / /login /docs; do
  curl -sS -o /dev/null -w "$route %{http_code}\n" "$PUBLIC_URL$route"
done
```

Record the actual URL, deployed commit SHA, timestamp with timezone, and all
three HTTP 200 statuses in #122. A wake-up/loading page alone is insufficient.

In the live browser, register a unique disposable account, generate and save a
look, then open Library and reopen it. Record its non-secret name/ID and all
four control values. Keep that look until the persistence check finishes. Perform
**Manual Deploy > Deploy latest commit** on the same web service; after health
recovers, log in with the same account, reopen that look, and compare its ID and
all saved parameters. Record before/after evidence and the successful redeploy
event. Exclude passwords, bearer tokens, and database credentials.

### Complete live suites are currently blocked

The HTTP target override is:

```sh
cd backend
BASE_URL="$PUBLIC_URL" FRONTEND_URL="$PUBLIC_URL" uv run pytest tests_integration
```

This alone cannot satisfy the complete suite: `test_stack.py` queries local
Compose PostgreSQL for registrations and restarts/polls the local app. Those
operations do not verify Render persistence or a Render redeploy.

`make e2e` also targets local Compose: `backend/integration/support.cjs` and
`e2e/playwright.config.ts` hard-code localhost, and multiple specs assert
absolute localhost URLs. Merely overriding Playwright's base URL is insufficient.
No valid unchanged invocation for the complete live suites is established.

Follow-up [#123](https://github.com/bakhytuly07-source/gradematch/issues/123)
records these runner blockers for grooming. Do not skip scenarios, weaken
assertions, change tests within #122's three-file scope, or count local passes
as live passes. After an authorized resolution, record each complete live
command, target URL, deployed commit and passing totals in #122. Until then,
the live-suite acceptance criteria remain unmet.
