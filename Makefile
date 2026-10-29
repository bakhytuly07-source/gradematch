.PHONY: up down logs ps integration

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
