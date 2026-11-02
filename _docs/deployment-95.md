# Single-image deployment verification — #95

Engineer run: 2026-11-02, macOS arm64 / local Docker 29.9.2. Issue remains open
for independent QA. No API operation or contract changes and no new dependencies.

The root multi-stage Dockerfile builds the SPA with Node 22 and `VITE_API_URL=/`,
then copies only static output into a Python 3.12 runtime. Compose runs `db` and
`app` on http://localhost:8091. The PostgreSQL named volume is preserved.
Runtime credentials come from Compose environment, outside the image build.

## Results

- `env -u NITRO_PRESET npm run build`: PASS; `.output/public/_shell.html` and
  `assets/` exist. `npm test`: 52 passed; `npx tsc --noEmit`: PASS.
- `cd backend && uv run pytest`: 182 passed, 1 PostgreSQL-specific test skipped
  with the default local database. Existing warnings remain (Starlette
  TestClient deprecation and intentional extreme-saturation overflow coverage).
- `uv run python ../_docs/check-contract.py`: PASS, all 13 operations unchanged.
  Static tests also count the generated schema's 13 operations with hosting on.
- `node --test backend/integration/run.test.cjs`: 3 passed.
- `docker build -t gradematch-95 .`: PASS. `make up`: PASS.
- `make integration`: PASS, 10 scenarios on the final image, including PostgreSQL
  account storage, owner isolation, CORS and persistence after `app` restart.
- `make down`: PASS after verification; no Compose containers remain and the
  named PostgreSQL volume is preserved.
- `make e2e`: PASS, unchanged guest, Library and Studio-session scenarios.
  Earlier runs reproduced the documented upload/auth-restoration race. The user
  explicitly authorized the Studio fix: defer editable UI until auth resolves.
  Existing ownership isolation and same-owner draft restoration tests still pass.
- `node backend/integration/static.cjs`: focused browser verification of direct
  and reloaded `/login` and `/library`, registration, save, `docker compose restart
  app`, fresh login with the original credentials, and the persisted saved look.
  Browser errors fail this check. A client-only root UI avoids hydrating `/`'s
  navigation state at other URLs; the HTML shell remains server-generated.
- Runtime image configured user `10001:10001`; `docker run --rm --entrypoint id
  gradematch-app -u` returned `10001`. Disposable containers accepted HTML HTTP
  requests on default 8091 and explicit `PORT=8092` (host mappings 18091/18092).
- Actual image startup with an invalid database URL failed before uvicorn.
  Entrypoint regression tests additionally verify exact migration-before-server
  ordering, propagation of migration exit status, and both port choices.
- Dockerfile/context review, image configuration/history and `/app` file inspection:
  no copied `.env`, credential files, application passwords/tokens, secret build
  arguments or database credentials. The base Python image's GPG fingerprint is
  public metadata. The build context uses an allowlist for application sources.
- Focused backend tests cover unset/nonexistent `STATIC_DIR`, shell fallback,
  real JavaScript MIME/content, missing assets and API JSON errors, docs/schema,
  symlink/traversal containment and API behavior with static hosting enabled.

## Runner compatibility

Existing integration/browser scenarios and assertions remain intact. Default
frontend URL is now 8091; browser-injected adapters use the same relative API
base as the UI. The CORS test targets the existing separate-development origin
5173, since Compose no longer sets `CORS_ORIGINS`. The persistence test's Compose
service reference necessarily changes from removed `backend` to `app`; its
restart, health and same-token assertions are unchanged.

The separate browser check cleans up its saved looks/sessions. Test accounts
remain because the API has no account-deletion endpoint. `make down` preserves
the database volume. Extraction quality and laptop performance release gates
remain separate from this deployment verification.
