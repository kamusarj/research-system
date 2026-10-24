#!/usr/bin/env bash
set -euo pipefail

phase6_db=$(mktemp /tmp/business-ai-migration-parity-XXXXXX.db)
cleanup() {
  rm -f "$phase6_db"
}
trap cleanup EXIT

export DATABASE_URL="sqlite:///$phase6_db"
uv run python -m alembic upgrade head
uv run python -m alembic check
head_before=$(uv run python -m alembic current | awk 'NR == 1 {print $1}')
uv run python -m alembic downgrade -1
uv run python -m alembic upgrade head
head_after=$(uv run python -m alembic current | awk 'NR == 1 {print $1}')

if [[ -z "$head_before" || "$head_before" != "$head_after" ]]; then
  echo "Migration parity failed: $head_before != $head_after" >&2
  exit 1
fi

echo "Migration parity passed at $head_after"
