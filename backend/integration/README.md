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
