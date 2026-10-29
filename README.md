# GradeMatch

Upload a reference photo, estimate its color style, preview it on a target, adjust
intensity/contrast/saturation/warmth, then export a 33³ `.cube` or PNG/JPEG.
Guests can try/export; accounts add a private saved-look Library.

**MVP engineering is reviewable; extraction quality is not release-approved.**
See the [release checks and evidence](./_docs/release-checks.md), including #18's
NO-GO, the current Library startup/upload timing failure, and pending laptop measurements. Estimates cannot recover an exact original
grade or separate lighting/scene colors reliably.

## Run the whole stack with Docker

Prerequisites: Git and Docker with the Docker Compose plugin (Docker Desktop
includes both). Start Docker first. Make is optional for the shortcuts below.
From the repository root, optionally copy the database configuration:

```sh
cp .env.example .env
```

Compose works without `.env`: `POSTGRES_DB`, `POSTGRES_USER`, and
`POSTGRES_PASSWORD` each default to `gradematch`. Edit `.env` to override them
before the first startup. Use URL-safe values because they are interpolated into
the backend connection URL. `.env` is ignored by Git. PostgreSQL initializes
credentials only for a new volume; changing `.env` does not update an existing
database's credentials.

```sh
docker compose up --build -d   # make up
docker compose ps            # make ps
docker compose logs -f       # make logs (Ctrl-C stops following logs)
docker compose down          # make down
```

Open the application at **http://localhost:3000** and API docs at
**http://localhost:8091/docs**. The three services are PostgreSQL 16 (`db`),
`backend`, and `frontend`. PostgreSQL is available only inside the Compose
network. The backend waits for PostgreSQL health, runs migrations, and serves
the API; the frontend waits for backend health. Allow up to 90 seconds after
startup for health checks to settle.

Accounts and saved looks persist in the named `postgres_data` volume across
backend restarts and `docker compose down` / `docker compose up -d`.
**`docker compose down -v` removes the database volume and all accounts and
saved looks.** The next startup initializes an empty database.

## Docker integration tests

From the repository root, run `make up` to start the stack, or run the complete
build, health wait, and HTTP integration suite with:

```sh
make integration
```

This requires the local Python/uv dependencies as well as Docker. Startup or test
failures return a nonzero exit code. To run only the suite against a running stack:

```sh
cd backend
uv run pytest tests_integration
# Optional HTTP target overrides (these are the defaults):
BASE_URL=http://localhost:8091 FRONTEND_URL=http://localhost:3000 uv run pytest tests_integration
```

`BASE_URL` changes the API target; `FRONTEND_URL` changes the frontend target.
A shared readiness gate fails within 10 seconds when services are unavailable,
printing `Integration stack unavailable` and an instruction to run `make up`.
Default `uv run pytest` collects only `tests/`, excluding integration scenarios.

The suite checks real HTTP services and uses local Compose for a read-only
Postgres registration check and a backend restart. Overrides must therefore point
to that same Compose stack. The persistence test restarts the backend, waits for
health, and checks the saved look with the original token. Avoid concurrent work
against this stack while it runs. Each account uses a unique email; tests delete
their own saved looks and revoke tokens where practical. Test accounts remain
because the API has no account deletion endpoint.

Integration runs preserve database volumes on success and failure, so consecutive
runs can use the same database. Stop services afterward with `make down`, which
also preserves volumes.

## Local setup without Docker

Prerequisites: Git, Python **3.12**, [uv](https://docs.astral.sh/uv/), Node.js
**22.12+** (Node 24 recommended), npm. Node 24.19/npm 11.9 were used for this
verification. Use the checked-in lockfiles; no external account is needed locally.

```sh
git clone https://github.com/bakhytuly07-source/gradematch.git
cd gradematch/backend
uv sync --locked --python 3.12
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8091
```

Keep the API running. In a second terminal, from the repository root:

```sh
cd frontend
npm ci
VITE_API_URL=http://localhost:8091 npm run dev -- --port 5173 --strictPort
```

Open **http://localhost:5173**. API docs: **http://localhost:8091/docs**.
First try generation/export without login, then register to save to the Library.
After account navigation, wait for authentication restoration before uploading;
if a selection is lost and Generate remains disabled, select the reference again.
The current startup/upload timing limitation is recorded in the release checks.
Do not use production credentials or real user images in disposable test runs.

## Configuration

- Backend `DATABASE_URL` defaults to an absolute SQLite URL for
  `backend/gradematch.db`, independent of the launch directory. Migrate before
  startup; tables are not created by startup. Set the same URL for migrations
  and server. A disposable custom example, run from `backend/`:

  ```sh
  mkdir -p ../work
  DATABASE_URL="sqlite:///$(pwd)/../work/local.db" uv run alembic upgrade head
  DATABASE_URL="sqlite:///$(pwd)/../work/local.db" uv run uvicorn app.main:app --port 8091
  ```

- `GRADEMATCH_STORAGE=orm` is the persistent default. Optional
  `GRADEMATCH_STORAGE=memory` runs without a database; accounts/looks disappear
  on restart. ORM access is SQLAlchemy only. Other database URLs need their
  appropriate driver; no additional driver is installed by these instructions.
- `CORS_ORIGINS` defaults to `http://localhost:5173`. Override with exact,
  comma-separated origins, for example
  `CORS_ORIGINS=https://app.example.com,https://preview.example.com` before the
  API command. No trailing slash or path; wildcards are rejected. An empty value
  denies all browser origins. CORS grants browser access, not authentication.
- `VITE_API_URL=http://localhost:8091` selects the real frontend adapter. It is
  a Vite startup/build variable; restart after changing it. To use the mock,
  leave it unset (also remove it from any local Vite env file):
  `env -u VITE_API_URL npm run dev -- --port 5173 --strictPort` from `frontend/`.
  Mock generation is synthetic and its accounts/Library do not survive reload.
- Real auth stores only the opaque token in tab-scoped sessionStorage keyed by
  API base URL, restores through getMe, and clears on logout/401 even if server
  revocation fails. Passwords are never stored. Server sessions last seven days.
  No secret belongs in frontend build variables.

## Tests and checks

Install both sets of dependencies above first. Tests use generated fixtures and
disposable migrated databases; the backend/frontend servers are not needed for
unit/API suites. Run from the named directories:

```sh
# From the repository root:
cd backend
uv run pytest
uv run python ../_docs/check-contract.py
# Focused contract/API parity coverage:
uv run pytest tests/test_api.py tests/test_download.py tests/test_render.py

# Switch from backend/ to frontend/:
cd ../frontend
npm test
npx tsc --noEmit
# Focused upload regressions:
npm test -- src/test/reference-upload.test.tsx src/services/file.test.ts
# Production compilation (use VITE_API_URL at build time for real API builds):
VITE_API_URL=http://localhost:8091 npm run build
```

Focused auth/account regressions, from `frontend/`:

```sh
npm test -- src/services/session.test.ts src/test/studio-session.test.tsx
```

Expected: all tests pass, contract check prints PASS, TypeScript exits zero, build
completes. Current results and pending manual checks are recorded in
[release-checks.md](./_docs/release-checks.md). Browser scenarios require an
existing Playwright installation and `/usr/bin/chromium`; they are optional
integration tooling, not project dependencies. See
[real browser reproduction](./backend/integration/README.md). The current
[verification run](./_docs/release-checks.md#current-verification-run) records
commands, results and artifact locations. Browse the [documentation index](./_docs/README.md)
for the contract audit and release evidence.

## Data and color limits

References accept JPEG/PNG/WebP up to **15,728,640 bytes inclusive** (UI: 15 MB).
Frontend metadata validation is followed by server signature/decoder checks,
with a 24-million-pixel guard and a ≤1024 px analysis copy. Uploaded originals
stay in memory, never disk/database. Guests create no saved records. Explicit
logged-in saves retain numeric style/settings, name/favorite/timestamps and an
optional JPEG reference thumbnail of exactly 256 px longest side.

Backend render/export share the same 33×33×33 float32 LUT, 107,811 interleaved RGB
samples with red grid index changing fastest. The browser applies those samples
for preview and edited-image export; `.cube` values round-trip to the same
float32 samples for the same settings. The mock's six-decimal writer is not real
API parity evidence. PNG is lossless; JPEG compression can change exported pixels.
The current canvas renderer previews a scaled image and caps image export at
6000 px; WebGL/worker rendering is not implemented.

Artistic operations assume encoded **SDR sRGB/Rec.709** values in 0..1, with no
HDR/log conversion or guarantee of cross-display color matching. A single finished
reference confounds scene, lighting and grade; current approximate extraction
has known photographic neutral/cool-transfer failures. Read the
[comparison boards and NO-GO](./backend/evaluation/README.md) before release.

[Contract](./openapi.yaml) · [13-operation audit](./_docs/contract-audit.md) ·
[Backend details](./backend/README.md) · [Product scope](./_docs/plan.md) ·
[Process](./_docs/process.md)
