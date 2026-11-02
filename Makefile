# Two services: PostgreSQL db + same-origin app at http://localhost:8091.
# Image runtime: PORT defaults to 8091; STATIC_DIR=/app/static enables the SPA.
.PHONY: up down logs ps restart integration e2e

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart app

ps:
	docker compose ps

integration:
	docker compose up -d --build --wait
	cd backend && uv run pytest tests_integration

# The runner waits for the same-origin app and API before launching managed Chromium.
e2e: up
	node backend/integration/run.cjs
