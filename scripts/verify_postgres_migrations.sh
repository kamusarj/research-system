#!/usr/bin/env bash
# Only use a new, disposable PostgreSQL database; never infer a URL from the app's .env.
set -Eeuo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
: "${DATABASE_URL:?Set DATABASE_URL to an empty disposable baa_ci_* PostgreSQL database}"
export DATABASE_URL
cd "$repo_dir/apps/api"
uv run --frozen python - <<'PY'
import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
if url.get_backend_name() != "postgresql" or not (url.database or "").startswith("baa_ci_"):
    raise SystemExit("Migration smoke test requires a disposable PostgreSQL database named baa_ci_*")
with create_engine(url).connect() as connection:
    if inspect(connection).get_table_names():
        raise SystemExit("Migration smoke test requires an empty database")
PY
uv run --frozen alembic upgrade head
uv run --frozen alembic check
uv run --frozen alembic downgrade -1
uv run --frozen alembic upgrade head
uv run --frozen alembic check
