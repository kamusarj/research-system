#!/usr/bin/env bash
# Cài cầu nối để API/worker dùng quota Claude Code, Codex và Antigravity đã đăng nhập trên máy.
# Chỉ dành cho chế độ cục bộ một chủ máy; chế độ nhóm luôn tắt cầu nối (DEC-062).
set -Eeuo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
config_dir="$HOME/.config/business-ai-agents"
token_file="$config_dir/ai-cli-bridge.token"
unit_dir="$HOME/.config/systemd/user"
unit_name=business-ai-agents-ai-cli-bridge.service
bridge_url=${AI_CLI_BRIDGE_URL:-http://172.17.0.1:11436}

for tool in python3 bwrap xdg-dbus-proxy; do
  command -v "$tool" >/dev/null || { echo "Thiếu $tool (sudo apt install bubblewrap xdg-dbus-proxy)" >&2; exit 1; }
done

install -d -m 700 "$config_dir"
if [[ ! -s "$token_file" ]]; then
  (umask 077 && python3 -c 'import secrets; print(secrets.token_urlsafe(48))' >"$token_file")
fi

install -d "$unit_dir"
sed "s|@REPO_DIR@|$repo_dir|g" "$repo_dir/ops/systemd/user/$unit_name" >"$unit_dir/$unit_name"
systemctl --user daemon-reload
systemctl --user enable --now "$unit_name"
systemctl --user restart "$unit_name"

# Ghi URL và token vào .env của repo để docker compose truyền cho API/worker.
env_file="$repo_dir/.env"
touch "$env_file"
token=$(<"$token_file")
for pair in "AI_CLI_BRIDGE_URL=$bridge_url" "AI_CLI_BRIDGE_TOKEN=$token"; do
  key=${pair%%=*}
  if grep -q "^$key=" "$env_file"; then
    python3 - "$env_file" "$key" "$pair" <<'PY'
import sys
from pathlib import Path
path, key, pair = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
lines = path.read_text().splitlines()
path.write_text("\n".join(pair if line.startswith(f"{key}=") else line for line in lines) + "\n")
PY
  else
    printf '%s\n' "$pair" >>"$env_file"
  fi
done

echo "Đã cài $unit_name, nghe tại $bridge_url."
echo "Đặt AI_PROVIDER và GRAPH_CHAT_DEFAULT_PROVIDER (claude_code | codex | antigravity) trong .env,"
echo "rồi tạo lại api/worker: systemctl --user restart business-ai-agents.service hoặc docker compose up -d."
