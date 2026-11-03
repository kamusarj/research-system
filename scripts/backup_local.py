#!/usr/bin/env python3
"""Consistent local/team backup; resume only application services running beforehand."""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

KIND = "business-ai-agents-scheduled-backup-v1"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def prune_completed(destination: Path, keep: int) -> None:
    if keep <= 0:
        return
    owned = []
    for path in destination.iterdir():
        manifest = path / "manifest.json"
        if path.is_symlink() or not path.is_dir() or not manifest.is_file():
            continue
        try:
            if json.loads(manifest.read_text()).get("kind") == KIND:
                owned.append(path)
        except (OSError, ValueError):
            continue
    for path in sorted(owned, reverse=True)[keep:]:
        shutil.rmtree(path)


def backup(repo: Path, destination: Path, keep: int) -> Path:
    os.umask(0o077)
    destination.mkdir(parents=True, mode=0o700, exist_ok=True)
    if destination.is_symlink():
        raise RuntimeError("Backup destination must not be a symlink")
    destination.chmod(0o700)
    with (destination / ".backup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        compose = ["docker", "compose", "--project-directory", str(repo), "-p", "businessaiagents"]
        if (repo / ".env.team").is_file():
            compose += [
                "--env-file",
                str(repo / ".env.team"),
                "-f",
                str(repo / "docker-compose.yml"),
                "-f",
                str(repo / "docker-compose.team.yml"),
            ]
        else:
            compose += [
                "-f",
                str(repo / "docker-compose.yml"),
                "-f",
                str(repo / "docker-compose.multi-user.yml"),
            ]

        def run(args, **kwargs):
            return subprocess.run(compose + args, check=True, stderr=subprocess.PIPE, **kwargs)

        running = set(
            run(
                ["ps", "--status", "running", "--services"], stdout=subprocess.PIPE, text=True
            ).stdout.split()
        )
        if "database" not in running:
            raise RuntimeError("Database is stopped; no service was started")
        resume = sorted(running & {"api", "worker"})
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = destination / stamp
        with tempfile.TemporaryDirectory(prefix=".partial-", dir=destination) as temporary:
            work = Path(temporary)
            try:
                if resume:
                    run(["stop", *resume], stdout=subprocess.DEVNULL)
                with (work / "postgres.dump").open("wb") as output:
                    run(
                        [
                            "exec",
                            "-T",
                            "database",
                            "sh",
                            "-ec",
                            'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',
                        ],
                        stdout=output,
                    )
                with (work / "postgres.dump").open("rb") as source:
                    run(
                        ["exec", "-T", "database", "pg_restore", "--list"],
                        stdin=source,
                        stdout=subprocess.DEVNULL,
                    )
                with (work / "document-objects.tar.gz").open("wb") as output:
                    run(
                        [
                            "run",
                            "--rm",
                            "--no-deps",
                            "-T",
                            "--entrypoint",
                            "tar",
                            "worker",
                            "-C",
                            "/var/lib/research-system/objects",
                            "-czf",
                            "-",
                            ".",
                        ],
                        stdout=output,
                    )
                with tarfile.open(work / "document-objects.tar.gz", "r:gz") as archive:
                    for member in archive:
                        if (
                            member.issym()
                            or member.islnk()
                            or not (member.isfile() or member.isdir())
                        ):
                            raise RuntimeError("Unexpected object archive entry")
                        if member.isfile():
                            with archive.extractfile(member) as source:
                                while source.read(1024 * 1024):
                                    pass
                files = {
                    path.name: {"bytes": path.stat().st_size, "sha256": digest(path)}
                    for path in work.iterdir()
                }
                (work / "manifest.json").write_text(
                    json.dumps(
                        {
                            "kind": KIND,
                            "created_at": datetime.now().astimezone().isoformat(),
                            "files": files,
                            "quiesced": resume,
                        },
                        indent=2,
                    )
                    + "\n"
                )
                for path in work.iterdir():
                    path.chmod(0o600)
                work.rename(target)
            finally:
                if resume:
                    run(["start", *resume], stdout=subprocess.DEVNULL)
        prune_completed(destination, keep)
        return target


def main() -> int:
    def interrupted(*_args):
        raise InterruptedError("Backup interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--destination", type=Path, default=Path.home() / "business-ai-agents-backups/scheduled"
    )
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()
    try:
        target = backup(args.repo.resolve(), args.destination, args.keep)
    except Exception:
        print("Backup failed; application services were resumed where possible")
        return 1
    print(f"Verified backup: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
