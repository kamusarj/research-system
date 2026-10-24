#!/usr/bin/env bash
set -Eeuo pipefail

# The repository now lives in the user's home directory, which is available
# before the graphical user service starts. Keep an override for future moves.
repo_dir=${BUSINESS_AI_REPO_DIR:-"$HOME/Desktop/Business AI Agents"}

if [[ ! -f "$repo_dir/docker-compose.yml" || ! -f "$repo_dir/docker-compose.multi-user.yml" ]]; then
  echo "Business AI Agents runtime configuration is unavailable at $repo_dir" >&2
  exit 75
fi

cd "$repo_dir"

# Khi đã cấu hình triển khai nhóm (`.env.team`), khởi động lại đúng bản đó thay vì chế độ cục bộ
# không xác thực. Ảnh phải được build trước bằng `make team-up`.
if [[ -f "$repo_dir/.env.team" && -f "$repo_dir/docker-compose.team.yml" ]]; then
  exec /usr/bin/docker compose \
    --env-file "$repo_dir/.env.team" \
    -f docker-compose.yml \
    -f docker-compose.team.yml \
    up -d --no-build --wait --wait-timeout 300
fi

exec /usr/bin/env \
  COMPOSE_PROJECT_NAME=businessaiagents \
  API_PORT=18000 \
  FRONTEND_PORT=13000 \
  API_CORS_ORIGINS=http://localhost:13000 \
  /usr/bin/docker compose \
    -f docker-compose.yml \
    -f docker-compose.multi-user.yml \
    up -d --no-build --wait --wait-timeout 180 database api worker frontend
