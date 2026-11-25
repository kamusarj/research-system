#!/usr/bin/env bash
# Deterministic proof; live provider, PostgreSQL and browser evidence are recorded separately.
set -Eeuo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir/apps/api"
uv lock --check
uv run --frozen ruff check . ../../scripts/backup_local.py
uv run --frozen python -m pytest -q
cd "$repo_dir/apps/discord-bot"
uv lock --check
uv run --frozen ruff check .
uv run --frozen python -m pytest -q
cd "$repo_dir/apps/web"
npm run lint
npm run typecheck
npm test
cd "$repo_dir"
bash -n scripts/team.sh scripts/verify_postgres_migrations.sh
sh -n apps/web/scripts/ensure-dependencies.sh
git diff --check
