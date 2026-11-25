#!/usr/bin/env python3
"""Validate a backup by default; --apply performs an explicit maintenance restore."""

import argparse
import fcntl
import json
import re
import signal
import stat
import subprocess
import tarfile
import uuid
from pathlib import Path, PurePosixPath

import backup_local

OBJECT_ROOT = "/var/lib/research-system/objects"
FILES = {"postgres.dump", "document-objects.tar.gz"}
APPLICATIONS = ["api", "worker", "frontend"]

# These small helpers travel over stdin/-c, so packaged team images need no source bind mount.
SPACE_CHECK = r"""
import os, sys
space = os.statvfs(sys.argv[1])
if int(sys.argv[2]) + 16 * 1024 * 1024 > space.f_bavail * space.f_frsize:
    raise RuntimeError("Insufficient space to stage restored objects safely")
"""

STAGE_OBJECTS = r"""
import shutil, sys, tarfile
from pathlib import Path, PurePosixPath
root, name = Path(sys.argv[1]), sys.argv[2]
if any(p.name.startswith(".restore-") for p in root.iterdir()):
    raise RuntimeError("An unfinished restore needs operator attention")
stage = root / name
stage.mkdir(mode=0o700)
with tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz") as archive:
    for entry in archive:
        parts = PurePosixPath(entry.name).parts
        if entry.name.startswith("/") or ".." in parts or "\\" in entry.name:
            raise RuntimeError("Unsafe archive path")
        if not (entry.isfile() or entry.isdir()) or (parts and parts[0].startswith(".restore-")):
            raise RuntimeError("Unsafe archive entry")
        if not parts:
            if entry.isdir():
                continue
            raise RuntimeError("Invalid archive root")
        target = stage.joinpath(*parts)
        if entry.isdir():
            target.mkdir(parents=True, exist_ok=True, mode=0o700)
        else:
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with archive.extractfile(entry) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            target.chmod(0o600)
"""

PROMOTE_OBJECTS = r"""
import sys
from pathlib import Path
root, stage_name, previous_name = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
stage, previous = root / stage_name, root / previous_name
previous.mkdir(mode=0o700)
for path in list(root.iterdir()):
    if path not in (stage, previous):
        path.rename(previous / path.name)
for path in list(stage.iterdir()):
    path.rename(root / path.name)
stage.rmdir()
"""

SMOKE_OBJECTS = r"""
import hashlib, sys
from pathlib import Path
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Attachment, DocumentGraphWorkspace, DocumentSourceVersion
from app.services.graph_invariants import check_graph_invariants
root = Path(sys.argv[1]).resolve()
with SessionLocal() as db:
    references = [(key, None, None) for key in db.scalars(select(Attachment.object_key))]
    references += [(key, None, None) for key in db.scalars(
        select(DocumentGraphWorkspace.storage_object_key))]
    references += list(db.execute(select(DocumentSourceVersion.object_key,
        DocumentSourceVersion.size_bytes, DocumentSourceVersion.content_hash)))
    for key, size, expected_hash in references:
        if key.startswith("minio://"):
            raise RuntimeError("Remote objects need an independently verified restore")
        path = (root / key).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise RuntimeError("A restored database reference has no local object")
        if size is not None and path.stat().st_size != size:
            raise RuntimeError("Restored object size mismatch")
        if expected_hash is not None:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_hash:
                raise RuntimeError("Restored object hash mismatch")
    if not check_graph_invariants(db).valid:
        raise RuntimeError("Restored graph invariants failed")
"""

CLEANUP_OBJECTS = r"""
import shutil, sys
from pathlib import Path
root, previous = Path(sys.argv[1]), sys.argv[2]
if not previous.startswith(".restore-previous-") or "/" in previous:
    raise RuntimeError("Invalid restore cleanup identity")
shutil.rmtree(root / previous)
"""

LIVE_SMOKE = r"""
(async () => {
  const base = 'http://127.0.0.1:3000/api/v1';
  const enabled = process.argv[1] === 'true';
  const health = await fetch(base + '/health');
  const auth = await fetch(base + '/auth/config');
  const data = await fetch(base + '/research');
  if (!health.ok || !auth.ok || (await auth.json()).enabled !== enabled
      || data.status !== (enabled ? 401 : 200)) {
    throw Error('Restored service/auth smoke failed');
  }
})().catch(() => process.exit(1));
"""


class RestoreError(RuntimeError):
    def __init__(self, stage: str, maintenance_started: bool):
        self.stage = stage
        self.maintenance_started = maintenance_started
        super().__init__(f"Restore failed at {stage}")


def verify_backup(directory: Path) -> dict[str, int]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Backup must be a real directory")
    for name in FILES | {"manifest.json"}:
        if not stat.S_ISREG((directory / name).lstat().st_mode):
            raise ValueError("Backup files must be regular files")
    manifest = json.loads((directory / "manifest.json").read_text())
    if not isinstance(manifest, dict) or manifest.get("kind") != backup_local.KIND:
        raise ValueError("Unrecognized backup manifest")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != FILES:
        raise ValueError("Incomplete backup manifest")
    for name in FILES:
        expected = files[name]
        if (
            not isinstance(expected, dict)
            or type(expected.get("bytes")) is not int
            or expected["bytes"] < 0
            or not isinstance(expected.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected["sha256"])
            or (directory / name).stat().st_size != expected["bytes"]
            or backup_local.digest(directory / name) != expected["sha256"]
        ):
            raise ValueError("Backup checksum or size mismatch")
    seen = set()
    object_count = unpacked_bytes = 0
    with tarfile.open(directory / "document-objects.tar.gz", "r:gz") as archive:
        for entry in archive:
            parts = PurePosixPath(entry.name).parts
            if (
                entry.name.startswith("/")
                or ".." in parts
                or "\\" in entry.name
                or not (entry.isfile() or entry.isdir())
                or (parts and parts[0].startswith(".restore-"))
                or parts in seen
                or (not parts and not entry.isdir())
            ):
                raise ValueError("Unsafe or repeated archive entry")
            seen.add(parts)
            if entry.isfile():
                size = 0
                with archive.extractfile(entry) as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        size += len(chunk)
                if size != entry.size:
                    raise ValueError("Truncated archive entry")
                unpacked_bytes += size
                object_count += 1
    return {"objects": object_count, "unpacked_bytes": unpacked_bytes}


def restore(
    repo: Path,
    directory: Path,
    env_file: Path | None = None,
    *,
    apply: bool = False,
    extra_compose_files: tuple[Path, ...] = (),
) -> dict:
    stage = "preflight"
    maintenance_started = False
    compose = []
    lock = None

    def run(arguments, **kwargs):
        return subprocess.run(
            compose + arguments,
            check=True,
            capture_output=True,
            timeout=600,
            **kwargs,
        )

    def objects(code, *args, **kwargs):
        return run(
            [
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "python",
                "worker",
                "-c",
                code,
                OBJECT_ROOT,
                *args,
            ],
            **kwargs,
        )

    try:
        compose = backup_local.compose_command(repo, env_file)
        for path in extra_compose_files:
            compose += ["-f", str(path.resolve(strict=True))]
        lock = backup_local.project_lock_path(repo).open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = verify_backup(directory)
        configuration = json.loads(run(["config", "--format", "json"], text=True).stdout)
        services = configuration["services"]
        environment = services["worker"]["environment"]
        requires_auth = (
            services.get("api", {}).get("environment", {}).get("AUTH_MODE", "local") == "local"
        )
        if environment.get("DOCUMENT_STORAGE_BACKEND", "local") != "local" or (
            environment.get("DOCUMENT_STORAGE_DIR", OBJECT_ROOT) != OBJECT_ROOT
        ):
            raise ValueError("Restore only supports the configured local object volume")
        running = set(run(["ps", "--status", "running", "--services"], text=True).stdout.split())
        if "database" not in running:
            raise ValueError("Database is stopped; no service was started")
        stage = "catalogue"
        with (directory / "postgres.dump").open("rb") as source:
            run(["exec", "-T", "database", "pg_restore", "--list"], stdin=source)
        stage = "capacity"
        objects(SPACE_CHECK, str(result["unpacked_bytes"]))
        if not apply:
            return {"mode": "verified", **result}

        resume = sorted(running & set(APPLICATIONS))
        stage = "quiesce"
        maintenance_started = True
        run(["stop", *APPLICATIONS])
        identity = uuid.uuid4().hex
        staging, previous = f".restore-stage-{identity}", f".restore-previous-{identity}"

        stage = "objects-stage"
        with (directory / "document-objects.tar.gz").open("rb") as source:
            objects(STAGE_OBJECTS, staging, stdin=source)
        stage = "database"
        with (directory / "postgres.dump").open("rb") as source:
            run(
                [
                    "exec",
                    "-T",
                    "database",
                    "sh",
                    "-ec",
                    "exec pg_restore --single-transaction --clean --if-exists --no-owner "
                    '-U "$POSTGRES_USER" -d "$POSTGRES_DB"',
                ],
                stdin=source,
            )
        stage = "objects-promote"
        objects(PROMOTE_OBJECTS, staging, previous)
        stage = "migrations"
        run(
            [
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--entrypoint",
                "sh",
                "worker",
                "-ec",
                "alembic upgrade head; alembic check",
            ]
        )
        stage = "smoke"
        objects(SMOKE_OBJECTS)
        if resume:
            stage = "resume"
            run(
                [
                    "up",
                    "-d",
                    "--no-deps",
                    "--no-build",
                    "--wait",
                    "--wait-timeout",
                    "300",
                    *resume,
                ]
            )
        if "frontend" in resume:
            stage = "live-smoke"
            run(["exec", "-T", "frontend", "node", "-e", LIVE_SMOKE, str(requires_auth).lower()])
        stage = "objects-cleanup"
        objects(CLEANUP_OBJECTS, previous)
        return {"mode": "restored", "resumed": resume, **result}
    except BaseException:
        if maintenance_started:
            # No resume in a finally block. Even a failed/partially successful start is stopped.
            try:
                run(["stop", *APPLICATIONS])
            except BaseException:
                pass
        raise RestoreError(stage, maintenance_started) from None
    finally:
        if lock is not None:
            lock.close()


def main() -> int:
    def interrupted(*_args):
        raise InterruptedError("Restore interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--env-file", type=Path, help="Team environment; otherwise use backup autodetection"
    )
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--compose-file", type=Path, action="append", default=[])
    parser.add_argument("--apply", action="store_true", help="Explicit maintenance restore intent")
    args = parser.parse_args()
    try:
        result = restore(
            args.repo.resolve(),
            args.backup,
            args.env_file,
            apply=args.apply,
            extra_compose_files=tuple(args.compose_file),
        )
    except RestoreError as error:
        print(f"Khôi phục thất bại ở bước {error.stage}.")
        if error.maintenance_started:
            print(
                "Không tự khởi động lại. Kiểm tra và giữ API/worker/frontend dừng; "
                "xem runbook khôi phục."
            )
        else:
            print("Chưa bắt đầu bảo trì hoặc ghi đè dữ liệu.")
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
