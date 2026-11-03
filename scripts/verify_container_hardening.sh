#!/usr/bin/env bash
# Kiểm thử cấu hình và ảnh bằng dữ liệu tổng hợp trong volume tạm; --live kiểm tra thêm runtime.
set -Eeuo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
image=${API_IMAGE:-businessaiagents-api}
[[ "${1:-}" == "" || "${1:-}" == "--live" ]] || exit 2

for variant in local multi-user team; do
  files=(-f docker-compose.yml)
  [[ "$variant" != local ]] && files+=(-f "docker-compose.$variant.yml")
  PUBLIC_URL=https://research.example.test POSTGRES_PASSWORD=fixture \
    docker compose "${files[@]}" config --format json | python3 -c '
import json, sys
services = json.load(sys.stdin)["services"]
for name in ("api", "worker"):
    service = services[name]
    assert service["user"] == "10001:10001", name + ": non-root user"
    assert service["read_only"], name + ": read-only root"
    assert service["cap_drop"] == ["ALL"], name + ": dropped capabilities"
    assert service["pids_limit"] == 256, name + ": bounded processes/threads"
    assert "no-new-privileges:true" in service["security_opt"], name + ": privilege boundary"
    assert service["depends_on"]["document-storage-init"]["condition"] == "service_completed_successfully"
    assert any(path.startswith("/tmp:") for path in service["tmpfs"]), name + ": temporary space"
    for mount in service["volumes"]:
        if mount["target"] == "/app":
            assert mount["read_only"], name + ": source mount"
init = services["document-storage-init"]
assert init["network_mode"] == "none"
assert not init.get("environment") and not init.get("secrets")
assert init["read_only"] and init["cap_drop"] == ["ALL"]
assert set(init["cap_add"]) == {"CHOWN", "DAC_OVERRIDE"}
assert init["image"] == services["api"]["image"]
assert len(init["volumes"]) == 1
assert init["volumes"][0]["target"] == "/var/lib/research-system/objects"
assert not any(v["type"] == "bind" for v in init["volumes"])
print("Compose security checks passed")'
done

volume="businessaiagents-hardening-check-$(date +%s)-$$"
network="$volume-net"
database="$volume-db"
docker volume create "$volume" >/dev/null
cleanup() {
  docker rm -f "$database" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null
}
trap cleanup EXIT
runtime=(--rm --pull never --network none --read-only --cap-drop ALL --pids-limit 256 \
  --security-opt no-new-privileges:true --tmpfs /tmp:rw,noexec,nosuid,size=512m,mode=1777 \
  --mount "type=volume,src=$volume,dst=/var/lib/research-system/objects")

# Quyền root chỉ dùng trong container không có mạng/khóa/mã bind-mount, như service khởi tạo.
docker run -i "${runtime[@]}" --user 0:0 --cap-add CHOWN --cap-add DAC_OVERRIDE \
  --entrypoint python "$image" - <<'PY'
from pathlib import Path
from app.prepare_storage import STORAGE_ROOT, prepare_storage

outside = Path("/tmp/outside")
outside.mkdir()
sentinel = outside / "sentinel"
sentinel.write_bytes(b"outside fixture")
sentinel.chmod(0o600)
before = sentinel.stat()
legacy = STORAGE_ROOT / "legacy"
legacy.mkdir(mode=0o700)
source = legacy / "original.bin"
source.write_bytes(b"legacy fixture")
source.chmod(0o600)
(STORAGE_ROOT / "file-link").symlink_to(sentinel)
(STORAGE_ROOT / "directory-link").symlink_to(outside, target_is_directory=True)
assert prepare_storage(STORAGE_ROOT) >= 2
assert prepare_storage(STORAGE_ROOT) == 0
assert source.stat().st_uid == 10001
assert source.stat().st_mode & 0o777 == 0o600
after = sentinel.stat()
assert (before.st_uid, before.st_gid, before.st_mode) == (after.st_uid, after.st_gid, after.st_mode)
assert sentinel.read_bytes() == b"outside fixture"
secret_fixture = STORAGE_ROOT / "group-readable-fixture"
secret_fixture.write_bytes(b"synthetic credential fixture")
import os
os.chown(secret_fixture, 0, 10001)
secret_fixture.chmod(0o640)
print("Legacy volume, private files, symlink isolation and idempotence passed")
PY

canary_code=$(cat <<'PY'
import asyncio
import io
import os
import subprocess
import tarfile
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from app.services.latex_compiler import compile_latex
from app.services.object_storage import LocalObjectStorage

assert os.getuid() == os.getgid() == 10001
assert Path("/sys/fs/cgroup/pids.max").read_text().strip() == "256"
status = Path("/proc/self/status").read_text()
assert "NoNewPrivs:\t1" in status
for line in status.splitlines():
    if line.startswith(("CapEff:", "CapBnd:")):
        assert int(line.split()[1], 16) == 0
for directory in ("/app", "/etc"):
    probe = Path(directory) / ".runtime-hardening-write-probe"
    try:
        probe.write_bytes(b"probe")
    except OSError:
        pass
    else:
        probe.unlink()
        raise AssertionError("Unexpected write access: " + directory)
root = Path("/var/lib/research-system/objects")
if os.environ.get("CHECK_LEGACY_FIXTURE") == "1":
    assert (root / "legacy/original.bin").read_bytes() == b"legacy fixture"
    assert (root / "group-readable-fixture").read_bytes() == b"synthetic credential fixture"

async def roundtrip(directory):
    storage = LocalObjectStorage(directory, max_bytes=1024)
    async def content():
        yield b"synthetic storage fixture"
    stored = await storage.put("nested/fixture.bin", content(), {})
    assert b"".join([chunk async for chunk in storage.open(stored.key)]) == b"synthetic storage fixture"
    await storage.delete(stored.key)
    assert not (Path(directory) / stored.key).exists()

with tempfile.TemporaryDirectory(prefix=".hardening-check-", dir=root) as directory:
    asyncio.run(roundtrip(directory))
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        entry = tarfile.TarInfo("restored.bin")
        entry.uid = entry.gid = 0
        entry.mode = 0o600
        entry.size = len(b"root-owned backup fixture")
        tar.addfile(entry, io.BytesIO(b"root-owned backup fixture"))
    subprocess.run(["tar", "--no-same-owner", "--no-same-permissions", "-xzf", "-", "-C", directory], input=archive.getvalue(), check=True)
    restored = Path(directory) / "restored.bin"
    assert restored.read_bytes() == b"root-owned backup fixture"
    assert restored.stat().st_uid == 10001
# Reproduce the shared-UID/thread-count regression before verifying the real compiler.
gate = threading.Event()
with ThreadPoolExecutor(max_workers=40) as pool:
    tasks = [pool.submit(gate.wait) for _ in range(40)]
    try:
        assert compile_latex(r"\documentclass{article}\begin{document}Runtime check\end{document}").startswith(b"%PDF")
    finally:
        gate.set()
with tempfile.TemporaryDirectory(prefix="hardening-ocr-") as directory:
    source = Path(directory) / "fixture.png"
    picture = Image.new("RGB", (700, 100), "white")
    ImageDraw.Draw(picture).text((10, 20), "RUNTIME STORAGE CHECK", fill="black", font=ImageFont.load_default(size=32))
    picture.save(source)
    result = subprocess.run(["tesseract", str(source), "stdout", "--psm", "6"], capture_output=True, text=True, check=True, timeout=20)
    assert "RUNTIME" in result.stdout
print("Non-root, capabilities, source/root protection, storage/restore, LaTeX and OCR passed")
PY
)
docker run "${runtime[@]}" -e CHECK_LEGACY_FIXTURE=1 --entrypoint python "$image" -c "$canary_code"

# Alembic phải chạy được bằng UID ứng dụng với /app chỉ đọc, trên PostgreSQL hoàn toàn cô lập.
database_image=$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["database"]["image"])')
docker network create --internal "$network" >/dev/null
docker run -d --rm --pull never --name "$database" --network "$network" \
  --network-alias hardening-db --tmpfs /var/lib/postgresql/data:rw,nosuid,size=256m \
  -e POSTGRES_USER=fixture -e POSTGRES_PASSWORD=fixture -e POSTGRES_DB=fixture \
  "$database_image" >/dev/null
ready=0
for attempt in {1..30}; do
  if docker exec "$database" pg_isready -U fixture -d fixture >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" == 1 ]] || { echo "Fixture PostgreSQL did not start" >&2; exit 1; }
docker run --rm --pull never --network "$network" --read-only --cap-drop ALL --pids-limit 256 \
  --security-opt no-new-privileges:true --tmpfs /tmp:rw,noexec,nosuid,size=512m,mode=1777 \
  -e DATABASE_URL=postgresql+psycopg://fixture:fixture@hardening-db:5432/fixture \
  --entrypoint sh "$image" -ec 'alembic upgrade head; alembic check'
if [[ "${1:-}" == "--live" ]]; then
  for container in businessaiagents-api-1 businessaiagents-worker-1; do
    docker exec "$container" python -c "$canary_code"
  done
fi
