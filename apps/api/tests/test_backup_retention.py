import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "local_backup", Path(__file__).parents[3] / "scripts/backup_local.py"
)
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


def test_retention_removes_only_verified_scheduled_backups(tmp_path):
    for name in ("20260101", "20260102", "20260103"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "manifest.json").write_text(json.dumps({"kind": backup.KIND}))
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "manifest.json").write_text('{"kind":"manual"}')
    incomplete = tmp_path / ".partial-fixture"
    incomplete.mkdir()
    backup.prune_completed(tmp_path, 2)
    assert not (tmp_path / "20260101").exists()
    assert (tmp_path / "20260102").exists() and (tmp_path / "20260103").exists()
    assert manual.exists() and incomplete.exists()


def test_retention_does_not_follow_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "manifest.json").write_text(json.dumps({"kind": backup.KIND}))
    destination = tmp_path / "backups"
    destination.mkdir()
    (destination / "old").symlink_to(outside, target_is_directory=True)
    backup.prune_completed(destination, 1)
    assert (outside / "manifest.json").exists()


def test_zero_retention_keeps_every_backup(tmp_path):
    directory = tmp_path / "old"
    directory.mkdir()
    (directory / "manifest.json").write_text(json.dumps({"kind": backup.KIND}))
    backup.prune_completed(tmp_path, 0)
    assert directory.exists()


def test_failed_dump_resumes_only_previously_running_services(tmp_path, monkeypatch):
    calls = []

    def run(argv, **_kwargs):
        calls.append(argv)
        if "ps" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="database\napi\n")
        if "exec" in argv:
            raise subprocess.CalledProcessError(1, argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(backup.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        backup.backup(tmp_path / "repo", tmp_path / "destination", 14)
    assert calls[-1][-2:] == ["start", "api"]
    assert all("worker" not in call for call in calls)
    assert not list((tmp_path / "destination").glob(".partial-*"))
