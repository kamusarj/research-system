#!/usr/bin/env bash
# Regression proof. PostgreSQL concurrency/migration and runtime smoke are recorded separately.
set -Eeuo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir/apps/api"
uv lock --check
uv run --frozen ruff check . ../../scripts/backup_local.py ../../scripts/restore_local.py
PYTHONPATH=. uv run --frozen python -m pytest
cd "$repo_dir/apps/discord-bot"
uv lock --check
uv run --frozen ruff check .
uv run --frozen python -m pytest
cd "$repo_dir/apps/web"
npm run lint
npm run typecheck
npm test
cd "$repo_dir"
bash -n scripts/team.sh scripts/verify_postgres_migrations.sh
git diff --check
