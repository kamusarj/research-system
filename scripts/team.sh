#!/usr/bin/env bash
# Vận hành bản triển khai nhóm (docker-compose.yml + docker-compose.team.yml + .env.team).
# Xem `Docs/Team Deployment Runbook.md`.
set -Eeuo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
env_file=${TEAM_ENV_FILE:-"$repo_dir/.env.team"}
cd "$repo_dir"

die() {
  printf 'team.sh: %s\n' "$*" >&2
  exit 1
}

[[ -f "$env_file" ]] || die "thiếu $env_file — chạy: cp .env.team.example .env.team rồi điền giá trị"

compose() {
  docker compose --env-file "$env_file" -f docker-compose.yml -f docker-compose.team.yml "$@"
}

env_value() {
  # Đọc một biến từ .env.team mà không source toàn bộ tệp (tệp có thể chứa khóa bí mật).
  local value
  value=$(grep -E "^$1=" "$env_file" | tail -n 1 | cut -d= -f2- || true)
  printf '%s' "${value:-${2:-}}"
}

check_env() {
  local password public_url
  password=$(env_value POSTGRES_PASSWORD)
  public_url=$(env_value PUBLIC_URL)
  [[ -n "$password" ]] || die "POSTGRES_PASSWORD đang trống trong $env_file"
  [[ "$password" =~ ^[A-Za-z0-9]+$ ]] ||
    die "POSTGRES_PASSWORD chỉ được gồm chữ và số vì được ghép vào DATABASE_URL"
  [[ "$password" != "research" ]] || die "POSTGRES_PASSWORD không được dùng giá trị mặc định 'research'"
  [[ "$public_url" == https://* ]] || die "PUBLIC_URL phải bắt đầu bằng https:// (cookie phiên là Secure)"
  compose config --quiet
}

create_user() {
  local role=$1 name=${NAME:-} email=${EMAIL:-}
  [[ -n "$name" && -n "$email" ]] || die "cần NAME=\"Họ tên\" EMAIL=ten@example.com"
  # Mật khẩu được nhập ẩn trong terminal (tối thiểu 12 ký tự) và không đi qua dòng lệnh.
  compose exec api python -m app.operations create-user \
    --name "$name" --email "$email" --role "$role" --password-stdin
}

db_password() {
  # POSTGRES_PASSWORD chỉ có hiệu lực khi volume được tạo lần đầu. Với dữ liệu đã có (ví dụ
  # chuyển từ chế độ cục bộ với mật khẩu `research`), đặt lại mật khẩu qua socket nội bộ.
  check_env
  compose up -d --wait database
  compose exec -T database sh -ec '
    printf "ALTER ROLE \"%s\" WITH PASSWORD :'"'"'new_password'"'"';\n" "$POSTGRES_USER" |
      psql -v ON_ERROR_STOP=1 -v new_password="$POSTGRES_PASSWORD" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null'
  echo "Đã đặt mật khẩu PostgreSQL theo POSTGRES_PASSWORD trong $(basename "$env_file")."
}

backup() {
  local root stamp target keep
  root=${BACKUP_DIR:-"$HOME/business-ai-agents-backups"}
  keep=${BACKUP_KEEP:-14}
  stamp=$(date +%Y%m%d-%H%M%S)
  target="$root/$stamp"
  mkdir -p "$target"
  chmod 700 "$root" "$target"
  if [[ "${BACKUP_QUIESCE:-0}" == "1" ]]; then
    compose stop api worker
    trap 'compose start api worker >/dev/null' EXIT
  fi
  # Sao lưu cơ sở dữ liệu trước rồi mới đến tệp: tệp tài liệu chỉ được thêm phiên bản mới, nên mọi
  # tham chiếu trong bản dump đều có đối tượng tương ứng trong bản lưu trữ.
  compose exec -T database sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    >"$target/postgres.dump"
  compose exec -T database pg_restore --list <"$target/postgres.dump" >/dev/null
  if [[ "${BACKUP_QUIESCE:-0}" == "1" ]]; then
    compose run --rm --no-deps -T --entrypoint tar worker \
      -C /var/lib/research-system/objects -czf - . >"$target/document-objects.tar.gz"
  else
    compose exec -T worker tar -C /var/lib/research-system/objects -czf - . \
      >"$target/document-objects.tar.gz"
  fi
  tar -tzf "$target/document-objects.tar.gz" >/dev/null
  chmod 600 "$target"/*
  echo "Đã sao lưu vào $target"
  if [[ "$keep" =~ ^[0-9]+$ && "$keep" -gt 0 ]]; then
    find "$root" -mindepth 1 -maxdepth 1 -type d -name '[0-9]*-[0-9]*' | sort | head -n "-$keep" |
      while read -r old; do rm -rf -- "$old"; done
  fi
}

verify() {
  local port bind base auth
  check_env
  port=$(env_value FRONTEND_PORT 3000)
  bind=$(env_value FRONTEND_BIND 127.0.0.1)
  [[ "$bind" == "0.0.0.0" ]] && bind=127.0.0.1
  base="http://$bind:$port"
  for service in database api worker frontend; do
    [[ -n "$(compose ps --status running --quiet "$service")" ]] || die "$service chưa chạy"
  done
  [[ -z "$(docker port "$(compose ps --quiet api)" 2>/dev/null || true)" ]] ||
    die "API không được mở cổng ra máy chủ"
  curl --fail --silent --show-error "$base/api/v1/health" >/dev/null
  auth=$(curl --fail --silent --show-error "$base/api/v1/auth/config")
  [[ "$auth" == *'"enabled":true'* ]] || die "xác thực chưa bật: $auth"
  status=$(curl --silent --output /dev/null --write-out '%{http_code}' "$base/api/v1/research")
  [[ "$status" == "401" ]] || die "API dữ liệu phải yêu cầu đăng nhập (nhận HTTP $status)"
  echo "Bản triển khai nhóm đạt kiểm tra: dịch vụ chạy, API ẩn sau proxy, bắt buộc đăng nhập."
}

usage() {
  cat <<'EOF'
Cách dùng: scripts/team.sh <lệnh>
  config        Kiểm tra .env.team và cấu hình Compose
  up            Build ảnh production rồi khởi động (giữ nguyên dữ liệu)
  down          Dừng và xóa container (không xóa volume dữ liệu)
  ps | logs     Trạng thái / nhật ký (logs nhận thêm tên service)
  owner         Tạo chủ sở hữu: NAME="..." EMAIL=... scripts/team.sh owner
  member        Tạo nhà nghiên cứu: NAME="..." EMAIL=... scripts/team.sh member
  db-password   Đổi mật khẩu PostgreSQL hiện có theo POSTGRES_PASSWORD
  backup        Sao lưu PostgreSQL + tệp tài liệu vào BACKUP_DIR (mặc định ~/business-ai-agents-backups)
  verify        Kiểm tra nhanh bản triển khai đang chạy
EOF
}

case "${1:-}" in
  config) check_env && echo "Cấu hình hợp lệ." ;;
  up)
    check_env
    compose build api frontend
    compose up -d --wait --wait-timeout 300
    verify
    ;;
  down) compose down ;;
  ps) compose ps ;;
  logs) shift; compose logs --tail 200 -f "$@" ;;
  owner) create_user owner ;;
  member) create_user researcher ;;
  db-password) db_password ;;
  backup) backup ;;
  verify) verify ;;
  *) usage; [[ -z "${1:-}" || "$1" == "-h" || "$1" == "--help" ]] || exit 2 ;;
esac
