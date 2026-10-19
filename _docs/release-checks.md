# MVP release checks (#66)

Engineering verification date: 2026-10-20 (Asia/Almaty). Historical browser/color
measurements below were recorded 2026-10-19. Current verification is recorded
separately under [Current verification run](#current-verification-run).
A checked box records evidence, not issue closure or overall release approval.

## Reproduce and review

Use [local setup and test commands](../README.md). Keep the three selected issues
[#1](https://github.com/bakhytuly07-source/gradematch/issues/1),
[#13](https://github.com/bakhytuly07-source/gradematch/issues/13), and
[#66](https://github.com/bakhytuly07-source/gradematch/issues/66) open for review.

- [x] Contract: [13-operation audit](./contract-audit.md),
  [authoritative OpenAPI](../openapi.yaml) and [repeatable check](./check-contract.py).
  13 unique interface/operation/table mappings, 68 local refs resolved, 13 JSON
  schemas valid, explicit security and response/body/status checks pass.
  This is not full OpenAPI validator certification.
- [x] Automated baseline: 51 frontend tests, TypeScript and 168 backend tests pass.
  Backend emits an existing httpx/TestClient deprecation warning. Tests include
  memory/ORM ownership, migrations, upload privacy, auth, real adapter mappings,
  stale preview requests and exact cube/render float32 parity.
- [ ] QA independently verifies acceptance criteria and decides issue closure.
- [ ] Extraction quality approval: **NO-GO** in [#18](https://github.com/bakhytuly07-source/gradematch/issues/18).
  [Evaluation narrative](../backend/evaluation/README.md),
  [measurements](../backend/evaluation/results.json),
  [neutral](../backend/evaluation/comparison-neutral.jpg),
  [cool](../backend/evaluation/comparison-cool.jpg),
  [split tone](../backend/evaluation/comparison-split.jpg),
  [muted](../backend/evaluation/comparison-muted.jpg) compare three revisions
  against known grades on portrait/landscape/indoor targets. Scene contamination
  and neutral/cool transfer failures remain. The authorized engineering
  continuation in [process](./process.md#authorized-m3-continuation-2026-10-19)
  does not change that verdict.
- [x] Historical real guest workflow [#55](https://github.com/bakhytuly07-source/gradematch/issues/55):
  [scenario and reproduction](../backend/integration/README.md),
  [browser results](../backend/integration/guest-results.json),
  [script](../backend/integration/guest.cjs). Upload validation/recovery, guest
  generation, target/sample, comparison modes, all controls/rapid changes,
  exact cube/render parity, PNG equality and JPEG error recorded; no page errors.
- [x] Historical real account/Library workflow [#56](https://github.com/bakhytuly07-source/gradematch/issues/56):
  [results](../backend/integration/library-results.json),
  [script](../backend/integration/library.cjs). Register/login/reload/logout,
  six Library operations, restored controls, saved-settings cube parity, blank
  rename rejection, foreign/missing equivalence, deletion isolation and revoked
  logout 401 clearing recorded; no page errors. Use a disposable migrated DB.
- [ ] Repeat real browser scenarios on the release candidate and intended browsers;
  review small-screen layout, keyboard uploads/controls, both comparisons and
  downloads. Existing headless Chromium evidence is not cross-browser approval.
- [ ] Confirm deployment API URL/CORS/database configuration and migrations using
  deployment-specific values; local examples contain no credentials.

## Performance evidence and pending qualification

Targets: generation **≤5 s** for a 15 MB reference; control-to-ready preview
**≤300 ms**. These are measurements on named fixtures/hosts, not universal bounds.

| Record | Hardware / browser | Input and method | Recorded times | Interpretation |
| --- | --- | --- | --- | --- |
| [Color experiment](../backend/evaluation/results.json) | Cloud Intel Xeon Platinum 8573C, Python 3.12.14 | 4000×3000 JPEG padded to 15,728,640 bytes; perf_counter decode + analysis + LUT, five runs | 264–311 ms | Under 5 s on this cloud fixture; not worst-case entropy or laptop qualification |
| [Generation endpoint](../backend/evaluation/api-results.json) | Same cloud Xeon / Python; no browser | 4000×3000 synthetic JPEG padded to 15,728,640 bytes; TestClient multipart request through response | 445–542 ms | Includes endpoint work; no real browser/network |
| [Browser renderer](../backend/evaluation/browser-results.json) | Same cloud Xeon, Chromium 154.0.8037.57, 3 exposed workers | 1024×768 and 4000×3000 pixels; canvas reads/LUT/writes + animation frame via performance.now | Preview cold 78 ms, warm 39–41 ms; full cold 617 ms, warm 571–972 ms | Renderer only; excludes controls/debounce/network/serialization |
| [Real guest UI](../backend/integration/guest-results.json) | Cloud AMD EPYC 9V74, Chromium 154.0.8037.57 | 15,728,640-byte padded reference; Date.now click→HTTP generation; controls→current export enabled includes debounce/HTTP; bundled sample/target photos | Generation 291 ms; preview 241, 252, 259, 247 ms | Under both targets on this fixture/host; concurrent workloads can exceed 300 ms |

PNG/JPEG export evidence in the guest record uses a 1024×1280 target: PNG mean
absolute channel error 0, JPEG ~0.439. The real UI report does not store reference
pixel dimensions or the sample dimensions for each preview timing; those fields
are **pending** for a complete benchmark report. Its reference bytes come from
reference-neutral.jpg plus padding, as shown by the script. Do not silently treat
that fixture as the separate 4000×3000 API benchmark.

Still pending: actual laptop CPU/OS/browser versions, representative high-entropy
15 MB files and pixel sizes, cold/warm repetitions under idle conditions, complete
control-to-visible-preview measurement per target dimension, and cross-browser
results. Record raw samples and methods alongside summaries. Synthetic padded
files exercise the byte limit but do not qualify worst-case decode/analysis.

## Validation for documentation changes

Run all documented suite/check commands. Smoke-test the setup using a disposable
`work/` database: migration upgrade twice succeeds, API starts on 8091, public
OpenAPI and generation work, missing bearer returns 401, Vite starts on 5173 and
serves the page. Build with the real API URL. Check relative Markdown links point
to existing files. These checks establish reproducible setup, not photographic
quality or manual browser qualification. Do not mark pending checks passed based
only on unit tests.

### Initial documentation verification (before auth/account regression fixes)

- Fresh `uv sync --locked` and `npm ci` succeeded on Python 3.12.14 /
  Node 24.19.0 / npm 11.9.0 without dependency or lockfile changes. This managed
  environment has a read-only home cache, so runs used
  `UV_CACHE_DIR=/tmp/gradematch-uv-cache` and
  `npm_config_cache=/workspace/gradematch/work/npm-cache`; normal writable-home
  machines need no overrides.
- `work/setup-smoke.db` migrated with `alembic upgrade head` twice successfully.
  A real Uvicorn process served port 8091: OpenAPI exposed 13 operations,
  generated JPEG upload returned 200 with StyleParams, missing credentials
  returned 401, and the default frontend-origin preflight returned 200 with
  the matching allow-origin header.
- Real-adapter Vite started on port 5173 with strictPort; HTTP GET returned
  GradeMatch HTML with status 200. Production `npm run build` with VITE_API_URL
  succeeded. Browser interactions were not rerun for this documentation check.
- Full suites: 40 frontend tests and 168 backend tests passed; TypeScript exited
  zero. Contract check passed; relative Markdown file links and diff whitespace
  checks passed. No claim is made that pending manual release checks passed.

## Current verification run

Rechecked on 2026-10-20 after the #52/#56 fixes and the cleared-upload fix #1.
Code snapshot: `dc31343` (includes `a07b5a5`, `ddca0d0`, `4fbdfba`).
[Retained current results](./release-evidence-2026-10-20.json) are separate from
historical records. Counts refer to tests tracked in this checkout.

| Directory | Command / check | Expected | Actual |
| --- | --- | --- | --- |
| backend/ | `uv sync --locked --python 3.12` | Locked environment installs/resolves | PASS; Python 3.12.14 |
| frontend/ | `npm ci` | Lockfile installs without edits | PASS; Node 24.19.0, npm 11.9.0 |
| backend/ | Same disposable DATABASE_URL, `uv run alembic upgrade head` twice | Schema created, repeat succeeds | PASS; work/release-docs.db |
| backend/ | `uv run uvicorn app.main:app --port 8091` | API starts; OpenAPI, guest generation, auth rejection and CORS work | PASS; real HTTP smoke check |
| frontend/ | `VITE_API_URL=http://localhost:8091 npm run dev -- --port 5173 --strictPort` | HTML served on 5173 | PASS |
| backend/ | `uv run pytest -q` | Full suite passes | PASS; 168 tests, existing upstream TestClient deprecation warning |
| backend/ | `uv run pytest tests/test_api.py tests/test_download.py tests/test_render.py -q` | API/render/export pass | PASS; 41 tests |
| backend/ | `uv run python ../_docs/check-contract.py` | Audit matches interface/contract | PASS; 13 mappings, 68 references, 13 schemas |
| frontend/ | `npm test -- --reporter=dot` | Full suite passes | PASS; 51 tests |
| frontend/ | `npm test -- src/test/reference-upload.test.tsx src/services/file.test.ts` | Upload replacement/boundary regressions pass | PASS; 11 tests |
| frontend/ | `npm test -- src/services/session.test.ts src/test/studio-session.test.tsx` | Auth races and private draft isolation pass | PASS; 15 tests |
| frontend/ | `npx tsc --noEmit` | Zero type errors | PASS |
| frontend/ | `VITE_API_URL=http://localhost:8091 npm run build` | Production compilation completes | PASS |
| repository root | `node backend/integration/guest.cjs` | Real guest flow, parity and exports pass | PASS; no page errors |
| repository root | `node backend/integration/library.cjs` | Full account/Library flow passes | FAIL; Generate stayed disabled after an early reference upload during Studio auth restoration |
| repository root | `node backend/integration/studio-session.cjs` | B cannot inherit A's saved warmth41 | PASS; defaults/no private preview/disabled export |

For restricted read-only-home environments only, use the cache overrides from
the initial verification section. Database/server commands use the same absolute
SQLite URL for both migrations and Uvicorn; this run used the README custom-URL
example with the filename `release-docs.db`. Servers must be ready before browser
scripts run. Those scripts require the environment's existing Playwright package
and `/usr/bin/chromium`; no dependency was added to the project.

The current guest run used cloud **AMD EPYC 9V45 96-Core Processor**, Chromium
**154.0.8037.57**, local Vite/Uvicorn and a single run. Generation was **207 ms**;
the four control-to-ready times were **191, 169, 173, 171 ms**, below the 5 s /
300 ms targets on this fixture. The reference is the 1024×1280 neutral JPEG,
padded to exactly **15,728,640 bytes**; target is the 1024×1280 bundled portrait,
within the 1600 px preview bound. Measurement is click→HTTP generation and
control→current export enabled (including debounce/HTTP), not a paint-completion
instrument. Raw settings, float32 parity and PNG/JPEG export measurements are in
the current JSON record. This is not a laptop or production performance claim.

An auth-ready diagnostic copy of the Library runner **passed** all six operations,
registration/login/reload/logout, blank rename/ownership/deletion isolation and
saved cube parity with no page errors. Its raw result is retained in the current
JSON under `library_auth_ready_diagnostic`. This confirms the remaining workflow
after waiting for the editor to mount and authentication to restore.

The failed unmodified Library runner is **not** marked passing based on the
historical report or the independent account-switch PASS. Uploading before
Studio auth restoration can lose the selection when its editor remounts.
Re-verification of that startup/upload timing remains pending. Ordinary six-
operation Library evidence from the historical run remains linked above.
The docs record this observed limitation; they do not manufacture release approval.

Release remains pending for the Library timing failure, independent QA closure,
extraction quality NO-GO, laptop/high-entropy qualification, cross-browser/manual
UX and deployment-specific checks. Setup/build/unit/API success does not resolve
those items.

### Reproduce the auth-ready Library diagnostic

Keep the same migrated API/frontend running. From the repository root, create a
scratch copy with an explicit editor/auth readiness step, then run it. This does
not modify the tracked runner or production code:

```sh
python3 - <<'PY'
from pathlib import Path
import json
root = Path.cwd()
source = (root / 'backend/integration/library.cjs').read_text()
source = source.replace("const root=path.resolve(__dirname,'../..');",
                        'const root=' + json.dumps(str(root)) + ';')
needle = "await page.getByRole('link',{name:'Studio',exact:true}).click();"
ready = """
  await page.getByRole('button',{name:'Generate Color Style',exact:true}).waitFor();
  await page.evaluate(async()=>{
    const {service}=await import('/src/services/index.ts');
    await service.getMe();
  });"""
assert needle in source
(root / 'work').mkdir(exist_ok=True)
(root / 'work/library-auth-ready.cjs').write_text(source.replace(needle, needle + ready))
PY
node work/library-auth-ready.cjs
```

Expected diagnostic result: all assertions pass and `work/library-results.json`
records the account/six-operation checks. The unmodified runner's early-upload
failure remains a separate result requiring engineering/QA follow-up. Treat any
new run's timings independently; do not overwrite historical release claims.
