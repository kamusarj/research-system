API_DIR := apps/api
WEB_DIR := apps/web

.PHONY: dev test lint build migrate seed

dev:
	docker compose up --build

test:
	cd $(API_DIR) && .venv/bin/python -m pytest
	cd $(WEB_DIR) && npm test

lint:
	cd $(API_DIR) && .venv/bin/python -m ruff check .
	cd $(WEB_DIR) && npm run lint

build:
	cd $(WEB_DIR) && npm run build

migrate:
	cd $(API_DIR) && .venv/bin/python -m alembic upgrade head

seed:
	cd $(API_DIR) && .venv/bin/python -m app.seed
