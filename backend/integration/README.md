# Real browser integration against Compose

See [root setup](../../README.md#browser-e2e-tests-against-compose) for Docker,
Node, existing Playwright tooling and managed browser installation. From the
repository root run `make e2e`. It starts Compose and waits for the production
frontend at http://localhost:3000 and real API at http://localhost:8091.
No development server or source-module HTTP imports are used.

Individual scenarios: `node backend/integration/guest.cjs`,
`node backend/integration/library.cjs`, `node backend/integration/studio-session.cjs`.
Run `make up` first; the scripts create `work/e2e` automatically. Reports are ignored local artifacts;
checked-in older reports are historical evidence, not current run output.

## Coverage

`work/e2e/guest-results.json` records real headless Chromium UI checks: client validation,
server corrupt-image rejection and recovery, a 15 MiB padded photographic JPEG,
sample and target uploads, both comparison modes, four controls/rapid changes,
float32-exact cube/render parity, PNG pixel equality and JPEG compression error.
No Library save request is made. Backend tests additionally inspect database
contents and upload handles to verify no guest records/original storage.

Measured on the recorded cloud AMD EPYC/Chromium host: generation 291 ms; control
to ready preview 241–259 ms (50 ms debounce included). These are local HTTP
measurements on the named fixture, not laptop or worst-case image qualification.
Concurrent test/build workloads can exceed 300 ms; benchmark on an idle host.
The browser still applies the backend LUT with the existing CPU canvas renderer;
no browser adjustment formulas were added. PNG/JPEG exports use the same current
LUT at original image size up to the existing 6000 px export limit. Export buttons
wait for current settings and obsolete download results are discarded.

## Accounts and Library (#56)

With Compose running:

```sh
node backend/integration/library.cjs
```

`work/e2e/library-results.json` records the actual Chromium scenario: register an account,
empty Library, generate and explicitly save from the editor, validate a 256 px
reference JPEG, list/open/rename/favorite/delete, reject a blank rename, reload
saved state, restore all four controls on a new target, and compare saved-settings
cube/render float32 samples. Real adapter instances verify every cross-owner
operation matches missing-id feedback, login after logout, and a second record
survives deletion. The UI finishes with revoked-token logout (401), a signed-out
reload, and a Library redirect requesting login. Tokens/passwords are excluded
from the report. Unique test accounts remain in Compose because no account deletion API exists;
saved looks are removed by cleanup, also on assertion failures when reachable.

Library load failures offer Retry. Account changes hide old records immediately;
obsolete loads/mutations cannot populate the next account. Per-record mutation
in-flight guards prevent duplicate favorite toggles/Enter-plus-blur renames.

Account-switch regression (#56), using the same Compose API/frontend:

```sh
node backend/integration/studio-session.cjs
```

This opens A's saved private settings (warmth 41), leaves Studio, logs out,
registers B and returns without a page reload. B must see default controls, no
private preview and disabled LUT export. Component tests additionally exercise
mounted account changes, unresolved authentication, stale private responses and
guest draft preservation through sign-in.


The helper compiles the checked-in real adapter and its installed validation
imports into a test-only browser script for API ownership/parity checks. The
application itself is always the Compose build. Guest export parity also loads
the existing canvas renderer from disk, retaining the original exact PNG and
float32 LUT checks. All four controls and guest generation retain their existing
performance assertions; timings depend on host load and are not laptop release
qualification. Cleanup touches only accounts registered by the current scenario.
Use `make down` to stop services without removing the database volume.

Runner/helper regression checks: `node --test backend/integration/run.test.cjs`.

## Verification for #94 (2026-10-29)

On Apple M5 with Playwright 1.62.1 / managed Chromium 151.0.7922.34:

- Two consecutive `make e2e` runs passed all three scenarios against the same
  Compose PostgreSQL volume, without resets.
- Second-run guest generation: 208 ms; four control updates: 134–145 ms.
  Cube float32 parity passed; PNG mean channel error was 0, JPEG was 0.413.
- Runner/helper tests: 3 passed. Forced readiness timeout and unavailable browser
  both exited nonzero with setup/URL diagnostics.
- Full backend suite: 178 passed, 1 PostgreSQL-specific test skipped in the
  default local suite. Full frontend suite: 51 passed across 12 files.

Local run logs: `/tmp/gradematch-94-e2e-first.log` and
`/tmp/gradematch-94-e2e-second.log`; regenerated reports: `work/e2e/`.
