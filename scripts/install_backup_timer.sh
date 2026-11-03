#!/usr/bin/env bash
set -Eeuo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
install_dir="$HOME/.local/lib/business-ai-agents/backup"
unit_dir="$HOME/.config/systemd/user"
install -d -m 700 "$install_dir"
install -m 500 "$repo_dir/scripts/backup_local.py" "$install_dir/backup_local.py"
install -d "$unit_dir"
/usr/bin/python3 - "$repo_dir" "$install_dir" "$unit_dir" <<'PY'
import sys
from pathlib import Path
repo, installed, units = map(Path, sys.argv[1:])
for name in ("business-ai-agents-backup.service", "business-ai-agents-backup.timer"):
    source = (repo / "ops/systemd/user" / name).read_text()
    (units / name).write_text(source.replace("@REPO_DIR@", str(repo)).replace("@INSTALL_DIR@", str(installed)))
PY
systemctl --user daemon-reload
systemctl --user enable --now business-ai-agents-backup.timer
echo "Đã lên lịch backup 02:30 theo giờ máy; chạy thử: systemctl --user start business-ai-agents-backup.service"
