#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"

if [[ -f .env.team ]]; then
  # Autostart chạy bản triển khai nhóm khi có `.env.team`; kiểm tra theo chế độ đó.
  /usr/bin/systemctl --user is-enabled business-ai-agents.service >/dev/null
  /usr/bin/cmp --silent scripts/start_local_autostart.sh "$HOME/.local/bin/business-ai-agents-autostart"
  exec scripts/team.sh verify
fi

COMPOSE_PROJECT_NAME=businessaiagents \
API_PORT=18000 \
FRONTEND_PORT=13000 \
API_CORS_ORIGINS=http://localhost:13000 \
  /usr/bin/docker compose \
    -f docker-compose.yml \
    -f docker-compose.multi-user.yml \
    config --quiet

COMPOSE_PROJECT_NAME=businessaiagents \
API_PORT=18000 \
FRONTEND_PORT=13000 \
API_CORS_ORIGINS=http://localhost:13000 \
  /usr/bin/docker compose \
    -f docker-compose.yml \
    -f docker-compose.multi-user.yml \
    config --format json |
  /usr/bin/python3 -c '
import json
import sys

config = json.load(sys.stdin)
services = config["services"]
expected = {"database", "api", "worker", "frontend"}
missing = expected.difference(services)
if missing:
    raise SystemExit(f"missing core services: {sorted(missing)}")
for name in sorted(expected):
    if services[name].get("restart") != "unless-stopped":
        raise SystemExit(f"{name}: restart policy is not unless-stopped")
for name in ("api", "frontend"):
    if "healthcheck" not in services[name]:
        raise SystemExit(f"{name}: missing startup healthcheck")

api_environment = services["api"].get("environment", {})
if str(api_environment.get("API_RELOAD")).lower() != "false":
    raise SystemExit("api: autostart must disable the development reloader")
if int(api_environment.get("API_WORKERS", 0)) < 2:
    raise SystemExit("api: autostart must use multiple workers")

published = {
    name: {str(port["published"]) for port in services[name].get("ports", [])}
    for name in ("api", "frontend")
}
api_ports = published["api"]
frontend_ports = published["frontend"]
if api_ports != {"18000"}:
    raise SystemExit(f"api: unexpected published ports {api_ports}")
if frontend_ports != {"13000"}:
    raise SystemExit(f"frontend: unexpected published ports {frontend_ports}")
'

/usr/bin/systemctl --user is-enabled business-ai-agents.service >/dev/null
/usr/bin/systemctl --user is-active business-ai-agents.service >/dev/null
/usr/bin/cmp --silent scripts/start_local_autostart.sh "$HOME/.local/bin/business-ai-agents-autostart"
/usr/bin/cmp --silent \
  ops/systemd/user/business-ai-agents.service \
  "$HOME/.config/systemd/user/business-ai-agents.service"

expected_api_source=$(/usr/bin/readlink --canonicalize "$repo_dir/apps/api")
expected_frontend_source=$(/usr/bin/readlink --canonicalize "$repo_dir/apps/web")

for service in database api worker frontend; do
  container_id=$(
    COMPOSE_PROJECT_NAME=businessaiagents \
    API_PORT=18000 \
    FRONTEND_PORT=13000 \
    API_CORS_ORIGINS=http://localhost:13000 \
      /usr/bin/docker compose \
        -f docker-compose.yml \
        -f docker-compose.multi-user.yml \
        ps --quiet "$service"
  )
  if [[ -z "$container_id" ]]; then
    echo "$service container is not running" >&2
    exit 1
  fi
  restart_policy=$(/usr/bin/docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$container_id")
  if [[ "$restart_policy" != "unless-stopped" ]]; then
    echo "$service restart policy is $restart_policy" >&2
    exit 1
  fi

  if [[ "$service" == "api" || "$service" == "worker" ]]; then
    expected_source=$expected_api_source
  elif [[ "$service" == "frontend" ]]; then
    expected_source=$expected_frontend_source
  else
    continue
  fi

  actual_source=$(
    /usr/bin/docker inspect \
      --format '{{range .Mounts}}{{if eq .Destination "/app"}}{{.Source}}{{end}}{{end}}' \
      "$container_id"
  )
  if [[ "$actual_source" != "$expected_source" ]]; then
    echo "$service source mount is $actual_source, expected $expected_source" >&2
    exit 1
  fi
done

/usr/bin/curl --fail --silent --show-error http://localhost:18000/api/v1/health >/dev/null
/usr/bin/curl --fail --silent --show-error http://localhost:13000/api/v1/health >/dev/null
/usr/bin/curl --fail --silent --show-error http://localhost:13000/ >/dev/null

echo "Local autostart verification passed on frontend 13000 and API 18000."
