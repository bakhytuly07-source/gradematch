# MVP release checks (#66)

Engineering verification date: 2026-10-20 (Asia/Almaty). Historical browser/color
measurements below were recorded 2026-10-19 and were not rerun for this docs task.
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
- [x] Automated baseline: 40 frontend tests, TypeScript and 168 backend tests pass.
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

### Documentation verification results (2026-10-20)

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
