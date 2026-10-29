.PHONY: up down logs ps integration e2e

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

integration:
	docker compose up -d --build --wait
	cd backend && uv run pytest tests_integration

# The runner waits for both HTTP services before launching managed Chromium.
e2e: up
	node backend/integration/run.cjs
