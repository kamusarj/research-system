#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"

API_WORKERS=4 \
DATABASE_POOL_SIZE=4 \
DATABASE_MAX_OVERFLOW=2 \
  docker compose -f docker-compose.yml -f docker-compose.multi-user.yml config --quiet

API_WORKERS=4 \
DATABASE_POOL_SIZE=4 \
DATABASE_MAX_OVERFLOW=2 \
  docker compose -f docker-compose.yml -f docker-compose.multi-user.yml config --format json |
  python3 -c '
import json
import sys

services = json.load(sys.stdin)["services"]
api = services["api"]
frontend = services["frontend"]
environment = api["environment"]

expected = {
    "API_RELOAD": "false",
    "API_WORKERS": "4",
    "DATABASE_POOL_SIZE": "4",
    "DATABASE_MAX_OVERFLOW": "2",
}
for name, value in expected.items():
    if str(environment.get(name)).lower() != value:
        raise SystemExit(f"api: expected {name}={value}, got {environment.get(name)!r}")

api_command = " ".join(api.get("command", [])) if isinstance(api.get("command"), list) else api.get("command", "")
frontend_command = " ".join(frontend.get("command", [])) if isinstance(frontend.get("command"), list) else frontend.get("command", "")
if "--workers" not in api_command or "--reload" not in api_command:
    raise SystemExit("api command must preserve dev reload and multi-worker branches")
if "npm ls --include=dev --depth=0" not in frontend_command:
    raise SystemExit("frontend multi-user mode must validate production and development dependencies")
if "npm ci --include=dev --no-audit --no-fund" not in frontend_command:
    raise SystemExit("frontend multi-user mode must sync the lockfile when the dependency volume is stale")
if "npm run build" not in frontend_command or "node .next/standalone/server.js" not in frontend_command:
    raise SystemExit("frontend multi-user mode must build and run the standalone production server")
'

echo "Knowledge Graph multi-user Compose profile is valid: 4 API workers, bounded DB pool, production frontend."
