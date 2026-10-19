# GradeMatch API

Python 3.12, FastAPI, uv. The authoritative wire contract is `../openapi.yaml`.

## Run and test

From `backend/`:

```sh
uv sync --locked
uv run uvicorn app.main:app --reload --port 8091
uv run pytest
```

The default application uses persistent ORM storage. Run migrations before
starting it. Docs: http://localhost:8091/docs. For isolated demos/tests,
`GRADEMATCH_STORAGE=memory` uses process-local accounts/sessions/Library with
no database access; data in that mode is lost on restart.

Initialize SQLAlchemy 2/Alembic storage:

```sh
uv run alembic upgrade head
GRADEMATCH_STORAGE=orm uv run uvicorn app.main:app --port 8091
```

Set `DATABASE_URL` for both migrations and the ORM server to override SQLite.
Default SQLite path is `backend/gradematch.db`, independent of the working
directory. Tables are created by migrations, never at application startup.
Database operations use ORM sessions; ORM regression tests remain in the suite.

## Injection and authentication

`create_app(users=MemoryUsers(), sessions=MemorySessions(...), looks=MemoryLooks(...))`
allows isolated repositories per application. Session and look clocks are
injectable for deterministic tests. `create_app(storage="orm")` selects persistence.

Emails are trimmed/lowercased and normalized duplicates are rejected atomically.
Passwords are bcrypt hashes of a fixed-length base64 SHA-256 prehash, supporting
passwords longer than bcrypt's 72-byte limit. Public users contain only id/email;
neither passwords nor hashes are logged or returned. Random opaque bearer tokens
are issued on registration/login; only their SHA-256 digests are stored. Sessions
expire after seven days. Logout revokes only the current session and returns an
empty 204; missing, malformed, unknown, expired and revoked tokens return 401.
The client clears its token locally even when logout returns 401.

## Images, privacy and Library

Guests can generate, render and export without an account or saved records.
Uploads are bounded to 15,728,640 bytes inclusive, with at most 1 MiB of multipart
overhead and 24 million decoded pixels. JPEG/PNG/WebP are checked by signature
and decoded content. Incomplete/malformed multipart is rejected; upload handles
close on success and failure, including incomplete parts, without disk rollover.
The orientation-correct analysis copy is at most 1024 px on its longest side.

Only explicit authenticated saves retain data: owner/id, name, favorite/timestamps,
numeric style parameters, four controls and an optional reference JPEG thumbnail.
Nonempty thumbnails must have exactly 256 px on their longest side; incorrect
sizes/formats are rejected. Re-encoding strips metadata. An empty thumbnail is
allowed and a trimmed blank name becomes `Untitled look`. Inputs and returned
nested settings are independent copies. Owners and credentials never appear in
public Look responses; missing and foreign-owned ids share the same 404.

Lists sort newest-created first, with opaque id descending as the stable tie-break
for equal timestamps, matching ORM mode. Rename and favorite update `updated_at`
without changing creation ordering. Favorite inversion is atomic and unsafe for
automatic retries. Deletion removes the complete owned record, including settings
and thumbnail; repeating deletion returns 404 and other records remain intact.
All timestamps are Unix epoch milliseconds. Ids are opaque strings.

## Color and export

The shared builder validates settings, constructs a B/G/R grid (red changes
fastest), adds luminance-weighted shadow/highlight tint scaled by look intensity,
applies Rec.709-weighted saturation (style multiplier blended by intensity, then
the saturation control), contrast about encoded 0.5, and red/blue warmth. It clips
once and returns a finite float32 33³ LUT in 0..1. These are artistic operations
on encoded SDR sRGB/Rec.709, not scene-linear/HDR transforms. Default controls
are 80/0/0/0; all four are required in requests. Zero intensity and zero other
controls give exact identity on the 1/32 grid. Other comparisons permit float32
rounding with absolute tolerance 1e-7.

Preview and `.cube` export use exactly the same builder. The pure writer validates
shape/range/finiteness and emits the required size/domain headers plus 35,937 RGB
rows. Nine significant decimal digits provide exact float32 round trips. Saved
look downloads pass settings to the guest export endpoint, without reading Library.
The browser applies the returned LUT and never recreates control formulas.

Generation integrates the conservative v2 neutral-anchor estimate evaluated in
[evaluation/README.md](evaluation/README.md). #18's quality **NO-GO remains**:
convincing photographic grade recovery and laptop qualification are unproven.
The user explicitly authorized continued M3 engineering despite that gate.
`uv run python evaluation/benchmark-api.py` reproduces the generation endpoint
benchmark; [api-results.json](evaluation/api-results.json) records 445–542 ms for
a padded 15 MiB, 12 MP JPEG on a cloud Xeon, not a laptop or worst-case photo.

## Frontend adapter and verification

From `frontend/`, `VITE_API_URL=http://localhost:8091 npm run dev -- --port 5173`
selects the real service; otherwise the existing mock remains. The adapter retains
its token in tab-scoped sessionStorage, uses bearer headers, converts LutData to Float32Array and maps
Look snake_case responses to UI camelCase. SaveLookInput, LutSettings and nested
StyleParams remain camelCase on the wire. getMe maps 401 to null.

The backend suite covers memory and ORM behavior. The complete memory journey
exercises all 13 contracted service operations with database sessions forbidden,
checks cross-user denial, and verifies uploads do not create Library records or
roll over to disk. `uv run pytest tests/test_startup.py` independently exercises
ASGI startup/shutdown without database access.

## Recorded dependency approval (#17)

On 2026-10-19 the user approved FastAPI, Uvicorn, NumPy, Pillow,
opencv-python-headless, bcrypt, python-multipart, pytest and HTTPX, including
uv-locked transitive dependencies. Existing SQLAlchemy/Alembic and contract-test
dependencies were retained from main; this M3 continuation added no packages.

Each ORM app resolves `DATABASE_URL` when constructed (`create_app(database_url=...)`
is available for isolated instances). Every request owns a session, closes it on
completion, and rolls back on exceptions. Writes commit explicitly; an uncommitted
transaction is discarded when its session closes. Non-SQLite URLs are passed to
SQLAlchemy unchanged and require an installed driver; no fallback is used.

Migration checks use disposable databases only. `uv run alembic upgrade head`
creates the shared ORM schema and is safe to repeat. To rebuild a **disposable**
database, set its `DATABASE_URL`, run `uv run alembic downgrade base`, then
`uv run alembic upgrade head`. Downgrading deletes account/Library data. The
migration environment resolves the URL on every invocation, like the app factory.

Look response mapping requires `updated_at` as epoch milliseconds but deliberately
omits it from the current UI model; creation ordering uses unchanged `created_at`.
The adapter validates required response fields, numeric settings and 107,811 LUT
samples, preserving red-fastest sample order. Nested settings and outbound save
keys remain camelCase exactly as specified in the contract.

The real browser adapter stores only the opaque access token in **sessionStorage**,
keyed by API base URL. It survives reload in that tab, expires with the tab/session
or server token lifetime (seven days), and is removed on 401/logout even when
revocation fails. Storage-disabled browsers fall back to memory. Passwords/user
records are never stored. `getMe` restores auth before Library requests; network
and server errors remain distinct from signed-out 401. Auth notifications clear
immediately on logout and stale restoration results cannot restore a former user.

`CORS_ORIGINS` is a comma-separated list of exact HTTP(S) origins (scheme, host,
optional port, no trailing slash/path). Default: `http://localhost:5173`; start
Vite with `--port 5173`. Deployment example:
`CORS_ORIGINS=https://app.example.com,https://preview.example.com`.
An explicitly empty value denies all browser origins; wildcards are rejected.
Authorization/Content-Type and GET/POST/PATCH/DELETE are permitted for allowed
origins. CORS controls browser response access; API authentication still applies.

Pending login/register responses are invalidated by logout or a newer sign-in.
Logout clears the local bearer immediately after capturing it for server
revocation. Obsolete responses (including logout 401) cannot restore an old token
or clear a newer account's credentials/notifications.
