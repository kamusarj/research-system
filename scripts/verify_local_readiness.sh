#!/usr/bin/env bash
# Mechanical story proof. Live provider/backup/browser evidence is recorded separately.
set -Eeuo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir/apps/api"
uv lock --check
uv run --frozen ruff check app tests ../../scripts/backup_local.py ../../scripts/verify_cli_isolation.py
uv run --frozen python -m pytest -q
cd "$repo_dir/apps/web"
npm run lint
npm run typecheck
npm test
npm run build
cd "$repo_dir"
bash -n scripts/install_ai_cli_bridge.sh scripts/install_backup_timer.sh scripts/verify_container_hardening.sh
git diff --check
