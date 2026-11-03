#!/usr/bin/env bash
# Cài cầu nối để API/worker dùng quota Claude Code, Codex và Antigravity đã đăng nhập trên máy.
# Chỉ dành cho chế độ cục bộ một chủ máy; chế độ nhóm luôn tắt cầu nối (DEC-062).
set -Eeuo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
config_dir="$HOME/.config/business-ai-agents"
install_dir="$HOME/.local/lib/business-ai-agents/ai-cli-bridge"
token_file="$config_dir/ai-cli-bridge.token"
unit_dir="$HOME/.config/systemd/user"
unit_name=business-ai-agents-ai-cli-bridge.service
bridge_url=${AI_CLI_BRIDGE_URL:-http://172.17.0.1:11436}

for tool in python3 bwrap dbus-daemon; do
  command -v "$tool" >/dev/null || { echo "Thiếu $tool" >&2; exit 1; }
done
/usr/bin/python3 -c 'import dbus; import gi' || {
  echo "Cần python3-dbus và python3-gi cho broker keyring giới hạn." >&2
  exit 1
}

install -d -m 700 "$config_dir"
if [[ ! -s "$token_file" ]]; then
  (umask 077 && python3 -c 'import secrets; print(secrets.token_urlsafe(48))' >"$token_file")
fi

install -d "$unit_dir"
install -d -m 700 "$install_dir"
for source in ai_cli_bridge.py ai_cli_keyring_proxy.py; do
  install -m 500 "$repo_dir/apps/api/app/$source" "$install_dir/$source"
done
/usr/bin/python3 - "$repo_dir/ops/systemd/user/$unit_name" "$unit_dir/$unit_name" "$install_dir" <<'PY'
import sys
from pathlib import Path
source, target, directory = sys.argv[1:]
Path(target).write_text(Path(source).read_text().replace("@INSTALL_DIR@", directory))
PY
systemctl --user daemon-reload
systemctl --user enable --now "$unit_name"
systemctl --user restart "$unit_name"

# Ghi URL và token vào .env của repo để docker compose truyền cho API/worker.
env_file="$repo_dir/.env"
touch "$env_file"
/usr/bin/python3 - "$env_file" "$token_file" "$bridge_url" <<'PY'
import os
import sys
import tempfile
from pathlib import Path
path, token_path, url = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
lines = path.read_text().splitlines()
for key, value in {"AI_CLI_BRIDGE_URL": url, "AI_CLI_BRIDGE_TOKEN": token_path.read_text().strip()}.items():
    pair = f"{key}={value}"
    if any(line.startswith(f"{key}=") for line in lines):
        lines = [pair if line.startswith(f"{key}=") else line for line in lines]
    else:
        lines.append(pair)
contents = "\n".join(lines) + "\n"
if contents != path.read_text():
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
        output.write(contents)
        temporary = Path(output.name)
    os.chmod(temporary, 0o600)
    temporary.replace(path)
PY

echo "Đã cài $unit_name, nghe tại $bridge_url."
echo "Đặt AI_PROVIDER và GRAPH_CHAT_DEFAULT_PROVIDER (claude_code | codex | antigravity) trong .env,"
echo "rồi tạo lại api/worker: systemctl --user restart business-ai-agents.service hoặc docker compose up -d."
