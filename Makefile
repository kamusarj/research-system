API_DIR := apps/api
WEB_DIR := apps/web
BOT_DIR := apps/discord-bot

.PHONY: dev test lint build migrate seed evaluate-graph-v2 verify-graph verify-migrations discord-bot \
	team-config team-up team-down team-ps team-logs team-owner team-member team-db-password \
	team-backup team-verify local-owner

dev:
	docker compose up --build

test:
	cd $(API_DIR) && .venv/bin/python -m pytest
	cd $(BOT_DIR) && .venv/bin/python -m pytest
	cd $(WEB_DIR) && npm test

lint:
	cd $(API_DIR) && .venv/bin/python -m ruff check .
	cd $(BOT_DIR) && .venv/bin/python -m ruff check .
	cd $(WEB_DIR) && npm run lint

build:
	cd $(WEB_DIR) && npm run build

migrate:
	cd $(API_DIR) && .venv/bin/python -m alembic upgrade head

seed:
	cd $(API_DIR) && .venv/bin/python -m app.seed

evaluate-graph-v2:
	cd $(API_DIR) && uv run python -m app.evaluation.graph_v2

verify-graph:
	cd $(API_DIR) && uv run python -m app.operations verify-graph

verify-migrations:
	cd $(API_DIR) && bash scripts/verify_migrations.sh

# The Discord gateway is opt-in: it refuses to start without an explicit allowlist.
discord-bot:
	docker compose --profile discord up -d --build discord-bot

# Triển khai cho nhóm nghiên cứu: cần `.env.team` (xem `.env.team.example` và
# `Docs/Team Deployment Runbook.md`). Ví dụ: make team-owner NAME="Linh" EMAIL=linh@example.com
team-config:
	scripts/team.sh config

team-up:
	scripts/team.sh up

team-down:
	scripts/team.sh down

team-ps:
	scripts/team.sh ps

team-logs:
	scripts/team.sh logs

# Tạo tài khoản chủ sở hữu cho runtime cục bộ (AUTH_MODE=local); mật khẩu nhập ẩn trong terminal.
local-owner:
	docker exec -it businessaiagents-api-1 python -m app.operations create-user \
		--name "$(NAME)" --email "$(EMAIL)" --role owner --password-stdin

team-owner:
	NAME="$(NAME)" EMAIL="$(EMAIL)" scripts/team.sh owner

team-member:
	NAME="$(NAME)" EMAIL="$(EMAIL)" scripts/team.sh member

team-db-password:
	scripts/team.sh db-password

team-backup:
	scripts/team.sh backup

team-verify:
	scripts/team.sh verify
