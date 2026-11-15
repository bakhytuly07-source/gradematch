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
