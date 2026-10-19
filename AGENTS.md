# GradeMatch (LUT & Color Style Matcher)

Web app: upload a reference photo, generate its color style as a 33x33x33 `.cube` 3D LUT, preview it on another photo, adjust 4 controls (look intensity, contrast, saturation, warmth), export the LUT or the edited image. Spec: `_docs/plan.md`.

## Stack

- Frontend: React + TypeScript (Vite), Vitest. Folder `frontend/`
- Backend: FastAPI, Python 3.12, `uv`, numpy, Pillow, opencv-python-headless. Folder `backend/`
- Database: SQLAlchemy 2 ORM + Alembic. SQLite by default, URL from `DATABASE_URL`
- Contract: `openapi.yaml` in the repo root

## Commands

Backend (run in `backend/`):
- `uv sync` - install dependencies
- `uv run pytest` - the whole backend suite
- `uv run uvicorn app.main:app --reload --port 8091` - run the API

Frontend (run in `frontend/`):
- `npm i` - install dependencies
- `npm run dev` - dev server
- `npm test` - the whole frontend suite

## Rules

- Do not add a dependency without asking
- All backend calls from the frontend go through one services layer (`frontend/src/services/`); `mockService` and the real service share one interface
- `openapi.yaml` is the contract. Change it first, then the code
- Database access only through the ORM. No raw SQL, no SQLite-specific features
- Uploaded images are never written to disk or the database. Only a 256 px thumbnail and numeric parameters are stored, and only when a logged-in user saves a look
- The exported `.cube` and the preview use the same LUT data from the backend
- Commit regularly, one meaningful change per commit
- GitHub issues are the only backlog. Labels: `mvp`, `post-mvp`, `user-test-bug`

## Documents

- `_docs/plan.md` - the product spec
- `_docs/process.md` - how work is organized, roles, orchestrator
- `_docs/task-template.md` - template for a groomed issue
- `_docs/team/pm.md`, `software-engineer.md`, `qa-engineer.md` - role definitions
- `_docs/brainstorm.md` - the brainstorm chat that produced the plan

When the user corrects you, update the relevant document so the same correction is not needed twice.
