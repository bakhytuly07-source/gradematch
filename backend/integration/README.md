# Real HTTP/browser integration

Use a disposable database and the existing environment Playwright/Chromium; no
project dependencies were added. From the repository root:

```sh
mkdir -p work
cd backend
DATABASE_URL=sqlite:////absolute/path/to/work/integration.db uv run alembic upgrade head
DATABASE_URL=sqlite:////absolute/path/to/work/integration.db uv run uvicorn app.main:app --port 8091
# Another terminal, from frontend/:
VITE_API_URL=http://localhost:8091 npm run dev -- --port 5173
# Another terminal, from repository root:
node backend/integration/guest.cjs
```

`guest-results.json` records real headless Chromium UI checks: client validation,
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

With the same real migrated backend/frontend running:

```sh
node backend/integration/library.cjs
```

`library-results.json` records the actual Chromium scenario: register an account,
empty Library, generate and explicitly save from the editor, validate a 256 px
reference JPEG, list/open/rename/favorite/delete, reject a blank rename, reload
saved state, restore all four controls on a new target, and compare saved-settings
cube/render float32 samples. Real adapter instances verify every cross-owner
operation matches missing-id feedback, login after logout, and a second record
survives deletion. The UI finishes with revoked-token logout (401), a signed-out
reload, and a Library redirect requesting login. Tokens/passwords are excluded
from the report. Disposable test accounts/looks remain only in the local test DB.

Library load failures offer Retry. Account changes hide old records immediately;
obsolete loads/mutations cannot populate the next account. Per-record mutation
in-flight guards prevent duplicate favorite toggles/Enter-plus-blur renames.

Account-switch regression (#56), using the same disposable migrated API/frontend:

```sh
node backend/integration/studio-session.cjs
```

This opens A's saved private settings (warmth 41), leaves Studio, logs out,
registers B and returns without a page reload. B must see default controls, no
private preview and disabled LUT export. Component tests additionally exercise
mounted account changes, unresolved authentication, stale private responses and
guest draft preservation through sign-in.
