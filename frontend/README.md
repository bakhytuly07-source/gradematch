# GradeMatch frontend

React/TypeScript with Vite and Vitest. Requires Node 22.12+ (Node 24 recommended)
and npm. From the repository root:

```sh
cd frontend
npm ci
VITE_API_URL=http://localhost:8091 npm run dev -- --port 5173 --strictPort
```

Open http://localhost:5173. Start the migrated backend first using the root
[setup guide](../README.md). To use the synthetic mock, leave VITE_API_URL unset
in both the shell and local Vite env files; no backend is then required.

Run checks from `frontend/` (no dev server required):

```sh
npm test
npm test -- src/test/reference-upload.test.tsx src/services/file.test.ts
npm test -- src/services/session.test.ts src/test/studio-session.test.tsx
npx tsc --noEmit
VITE_API_URL=http://localhost:8091 npm run build
```

Expected: full/focused suites pass, TypeScript exits zero and production build
completes. See [actual run results](../_docs/release-checks.md#current-verification-run),
[release evidence](../_docs/release-checks.md), and the
[13-operation contract audit table](../_docs/contract-audit.md#operation-audit-table).
The backend suite runs separately from `backend/` with `uv run pytest`.

All backend calls go through `src/services/`; mock and real adapters share one
interface. Mock accounts/Library are in memory only. Actual uploaded originals
are processed in memory; only explicit authenticated saves persist thumbnail and
numeric settings. See the root guide for privacy, token lifetime, SDR assumptions
and the unresolved extraction quality NO-GO.
