# Deploy GradeMatch on Railway

Use the existing root Dockerfile: it builds the frontend and serves the SPA and
API together. No separate frontend service, build variables, or API URL is needed.

## Create the services

1. Sign in to Railway, click **New Project → Deploy from GitHub repo**, connect
   GitHub if prompted, and grant access to `bakhytuly07-source/gradematch`.
2. Select that repository. Open the new app service's **Settings → Source**;
   select branch `main` and leave the root directory at the repository root.
   Railway detects `Dockerfile`. Do not override the start command: the image's
   entrypoint checks readiness, runs migrations, then starts Uvicorn.
3. In the project canvas click **New → Database → Add PostgreSQL**. Wait for the
   database service (normally named `Postgres`) to become available.
4. Open the **app** service's **Variables** tab, click **New Variable**, enter
   `DATABASE_URL`, and use **Add Reference** to select `Postgres → DATABASE_URL`.
   The value is `${{Postgres.DATABASE_URL}}`; if you renamed the database service,
   select that service in the reference picker instead. Do not copy its resolved
   credential or use its public URL. Both services must use the same environment.
5. Leave `CORS_ORIGINS` **unset** for this same-origin deployment. Leave `PORT`
   platform-managed; the app binds to `0.0.0.0:$PORT` (8091 when unset).
6. Review and deploy the pending changes. The root `railway.toml` requests the
   Dockerfile builder, `/docs` health check, and restart on failure (10 retries).
   In **Settings → Deploy**, verify health check `/docs` and restart policy
   **On Failure**, maximum retries **10**. In **Settings → Build**, verify the
   Dockerfile path is `Dockerfile`.

Railway's [Config as Code documentation](https://docs.railway.com/config-as-code)
currently states that new services cannot opt into TOML configuration and that
existing support ends 2026-12-01. The requested `railway.toml` is included for
compatible services. For new services set the same values in the dashboard as
above; the existing Dockerfile and entrypoint work without platform-specific
application changes. Confirm this platform limitation before relying on TOML.
See also Railway's [Docker deployment guide](https://railway.com/guides/docker-compose).

## Publish and verify

1. Open the app service's **Settings → Networking → Public Networking** and
   click **Generate Domain**. Use the detected app port (`PORT`), not a database
   port. Railway supplies HTTPS.
2. Visit `https://<generated-domain>/docs`. Confirm HTTP **200** in the browser
   Network panel, or run `curl -o /dev/null -s -w '%{http_code}\n' https://<generated-domain>/docs`.
   Then open `/` to use GradeMatch. Railway's deployment health check also uses
   `/docs`, after readiness and migrations have completed.

## Read failures and logs

Open the app service's **Deployments**, click the deployment, and select
**Build Logs** for Docker/frontend/dependency failures, or **Deploy Logs** for
runtime startup. Alternatively, open **Observability → Log Explorer** and filter
by the app service. See [Railway logs](https://docs.railway.com/observability/logs).

Startup prints `Waiting for database readiness (30-second timeout).`, then
`Database ready; starting migrations.`. Failed connection attempts retry after
one second; each runs in a subprocess bounded by the remaining deadline and at
most one second. Driver and DNS hangs cannot indefinitely block startup.
`Database readiness timeout after 30 seconds; startup aborted.` means no
migrations or server ran. Check the database service status, same-environment
reference, and private networking, then redeploy. Connection errors and resolved
database credentials are suppressed by the readiness probe.

Alembic migration logs follow readiness. A nonzero migration result prevents
Uvicorn from starting; inspect the migration error before retrying. Successful
startup ends with Uvicorn listening on `0.0.0.0:<port>`. If a health check fails,
check these runtime logs and the configured target port and `/docs` path.
Keep credentials in runtime variables; never paste resolved variables into logs,
issues, source files, build arguments, or screenshots.

Local SQLite remains the default when `DATABASE_URL` is unset. Railway requires
the PostgreSQL reference; the runtime image has no persistent SQLite storage.
