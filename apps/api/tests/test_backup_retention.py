import importlib.util
import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "local_backup", Path(__file__).parents[3] / "scripts/backup_local.py"
)
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


@pytest.fixture(autouse=True)
def isolated_project_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "project_lock_path", lambda _repo: tmp_path / "project.lock")


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
    assert all(call[call.index("-p") + 1] == "businessaiagents" for call in calls)
    assert not list((tmp_path / "destination").glob(".partial-*"))


@pytest.mark.parametrize("selection", ["explicit", "auto"])
def test_team_backup_quiesces_deletes_and_preserves_custom_env(tmp_path, monkeypatch, selection):
    calls = []
    running = {"api", "database"}  # An already stopped worker must stay stopped afterwards.
    repo = tmp_path / "repo"
    repo.mkdir()
    env_file = repo / ".env.team" if selection == "auto" else tmp_path / "private-team.env"
    env_file.write_text("COMPOSE_PROJECT_NAME=isolated-team\n")
    objects = {"document.txt": b"verified source"}

    def run(argv, **kwargs):
        calls.append(argv)
        if "ps" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="\n".join(running))
        if "stop" in argv:
            running.discard("api")
        elif "pg_dump" in " ".join(argv):
            kwargs["stdout"].write(b"document.txt")
            # The scheduled destination must not enter a second quiesce/resume window.
            with pytest.raises(BlockingIOError):
                backup.backup(repo, tmp_path / "scheduled", 14)
            # A concurrent application delete could run here if the API were still running.
            if "api" in running:
                objects.clear()
        elif "--entrypoint" in argv:
            with tarfile.open(fileobj=kwargs["stdout"], mode="w:gz") as archive:
                for name, data in objects.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
        elif "start" in argv:
            running.add("api")
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(backup.subprocess, "run", run)
    destination = tmp_path / "backups"
    legacy = destination / "20260101-rollback"
    legacy.mkdir(parents=True)
    target = backup.backup(
        repo, destination, 1, env_file=env_file if selection == "explicit" else None
    )
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["quiesced"] == ["api"]
    with tarfile.open(target / "document-objects.tar.gz") as archive:
        assert (target / "postgres.dump").read_text() in archive.getnames()
    assert running == {"api", "database"}
    assert legacy.exists()
    assert all(str(env_file) in call and "-p" not in call for call in calls)
    assert calls[-1][-2:] == ["start", "api"]


def test_unfinished_restore_is_never_published_or_pruned_as_a_verified_backup(
    tmp_path, monkeypatch
):
    destination = tmp_path / "backups"
    old = destination / "20260101"
    old.mkdir(parents=True)
    (old / "manifest.json").write_text(json.dumps({"kind": backup.KIND}))
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if "ps" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="database\n")
        if "pg_dump" in " ".join(argv):
            kwargs["stdout"].write(b"synthetic dump")
        elif "--entrypoint" in argv:
            with tarfile.open(fileobj=kwargs["stdout"], mode="w:gz") as archive:
                entry = tarfile.TarInfo("./.restore-stage-interrupted")
                entry.type = tarfile.DIRTYPE
                archive.addfile(entry)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(backup.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="unfinished restore"):
        backup.backup(tmp_path / "repo", destination, 1)
    assert old.exists()
    assert not list(destination.glob(".partial-*"))
    assert sorted(path.name for path in destination.iterdir() if path.is_dir()) == [old.name]
    assert not any("start" in call for call in calls)
