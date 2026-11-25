"""Restore is a maintenance boundary: failures never fall through to a service restart."""

import fcntl
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC = importlib.util.spec_from_file_location("guarded_restore", SCRIPTS / "restore_local.py")
    restore = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(restore)
finally:
    sys.path.pop(0)


def manifest(directory):
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "kind": restore.backup_local.KIND,
                "files": {
                    name: {
                        "bytes": (directory / name).stat().st_size,
                        "sha256": restore.backup_local.digest(directory / name),
                    }
                    for name in restore.FILES
                },
            }
        )
    )


@pytest.fixture
def backup(tmp_path, monkeypatch):
    directory = tmp_path / "backup"
    directory.mkdir()
    (directory / "postgres.dump").write_bytes(b"synthetic dump fixture")
    with tarfile.open(directory / "document-objects.tar.gz", "w:gz") as archive:
        entry = tarfile.TarInfo("nested/source.txt")
        entry.size = 7
        archive.addfile(entry, io.BytesIO(b"content"))
    manifest(directory)
    monkeypatch.setattr(restore.backup_local, "project_lock_path", lambda _: tmp_path / "lock")
    (tmp_path / "team.env").write_text("COMPOSE_PROJECT_NAME=synthetic-team\n")
    return directory


def docker_fixture(
    monkeypatch, *, failure=None, running="database\napi\nworker\nfrontend", on_stop=None
):
    calls = []

    def run(argv, **kwargs):
        command = next(
            i for i, arg in enumerate(argv) if arg in {"config", "ps", "exec", "stop", "run", "up"}
        )
        args = argv[command:]
        calls.append(argv)
        if args[:3] == ["config", "--format", "json"]:
            stage = "preflight"
            output = json.dumps({"services": {"worker": {"environment": {}}}})
        elif args[:1] == ["ps"]:
            stage, output = "ps", running
        elif "--list" in args:
            stage, output = "catalogue", "synthetic catalogue"
        elif restore.SPACE_CHECK in args:
            stage, output = "capacity", ""
        elif args[:1] == ["stop"]:
            stage, output = "quiesce", ""
            if on_stop is not None:
                on_stop()
        elif restore.STAGE_OBJECTS in args:
            stage, output = "objects-stage", ""
        elif any("pg_restore --single-transaction" in arg for arg in args):
            stage, output = "database", ""
        elif restore.PROMOTE_OBJECTS in args:
            stage, output = "objects-promote", ""
        elif "alembic upgrade head; alembic check" in args:
            stage, output = "migrations", ""
        elif restore.SMOKE_OBJECTS in args:
            stage, output = "smoke", ""
        elif restore.CLEANUP_OBJECTS in args:
            stage, output = "objects-cleanup", ""
        elif args[:1] == ["up"]:
            stage, output = "resume", ""
        elif restore.LIVE_SMOKE in args:
            stage, output = "live-smoke", ""
        else:
            pytest.fail(f"Unexpected synthetic Docker command: {args[:3]}")
        if stage == failure:
            raise subprocess.CalledProcessError(1, argv, stderr="synthetic private upstream error")
        return subprocess.CompletedProcess(argv, 0, stdout=output if kwargs.get("text") else b"")

    monkeypatch.setattr(restore.subprocess, "run", run)
    return calls


def invoke(tmp_path, backup, *, apply=True):
    return restore.restore(tmp_path, backup, tmp_path / "team.env", apply=apply)


@pytest.mark.parametrize(
    "stage",
    [
        "preflight",
        "catalogue",
        "capacity",
        "quiesce",
        "objects-stage",
        "database",
        "objects-promote",
        "migrations",
        "smoke",
        "objects-cleanup",
        "resume",
        "live-smoke",
    ],
)
def test_failure_at_each_stage_does_not_fall_through_to_resume(
    tmp_path, monkeypatch, backup, stage
):
    calls = docker_fixture(monkeypatch, failure=stage)
    with pytest.raises(restore.RestoreError) as error:
        invoke(tmp_path, backup)
    assert error.value.stage == stage
    assert "private" not in str(error.value)
    starts = [call for call in calls if "up" in call]
    if stage not in {"resume", "live-smoke", "objects-cleanup"}:
        assert not starts
    else:
        assert len(starts) == 1
        assert calls[-1][-4:] == ["stop", *restore.APPLICATIONS]


def test_checksum_failure_happens_before_any_docker_or_stop(tmp_path, monkeypatch, backup):
    calls = docker_fixture(monkeypatch)
    (backup / "postgres.dump").write_bytes(b"tampered")
    with pytest.raises(restore.RestoreError) as error:
        invoke(tmp_path, backup)
    assert error.value.stage == "preflight" and not error.value.maintenance_started
    assert not calls


def test_backup_lock_stays_held_until_failed_restore_has_stopped_services(
    tmp_path, monkeypatch, backup
):
    checked = []

    def on_stop():
        with (tmp_path / "lock").open("a") as competing:
            with pytest.raises(BlockingIOError):
                fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
        checked.append(True)

    docker_fixture(monkeypatch, failure="database", on_stop=on_stop)
    with pytest.raises(restore.RestoreError):
        invoke(tmp_path, backup)
    assert len(checked) == 2


def test_archive_size_in_manifest_is_checked_before_quiesce(backup):
    metadata = json.loads((backup / "manifest.json").read_text())
    metadata["files"]["document-objects.tar.gz"]["bytes"] += 1
    (backup / "manifest.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        restore.verify_backup(backup)


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../outside", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("link", tarfile.SYMTYPE),
        ("hardlink", tarfile.LNKTYPE),
        ("device", tarfile.CHRTYPE),
        (".restore-stage-old/file", tarfile.REGTYPE),
    ],
)
def test_unsafe_archives_are_rejected_even_with_matching_checksum(backup, name, kind):
    with tarfile.open(backup / "document-objects.tar.gz", "w:gz") as archive:
        entry = tarfile.TarInfo(name)
        entry.type = kind
        archive.addfile(entry)
    manifest(backup)
    with pytest.raises(ValueError):
        restore.verify_backup(backup)


def test_duplicate_normalized_paths_are_rejected(backup):
    with tarfile.open(backup / "document-objects.tar.gz", "w:gz") as archive:
        archive.addfile(tarfile.TarInfo("./duplicate"))
        archive.addfile(tarfile.TarInfo("duplicate"))
    manifest(backup)
    with pytest.raises(ValueError):
        restore.verify_backup(backup)


def test_verify_only_never_stops_or_starts_services(tmp_path, monkeypatch, backup):
    calls = docker_fixture(monkeypatch)
    assert invoke(tmp_path, backup, apply=False) == {
        "mode": "verified",
        "objects": 1,
        "unpacked_bytes": 7,
    }
    assert all("stop" not in call and "up" not in call for call in calls)


def test_success_orders_staging_before_transaction_and_smoke_before_resume(
    tmp_path, monkeypatch, backup
):
    calls = docker_fixture(monkeypatch)
    result = invoke(tmp_path, backup)
    stage = next(i for i, call in enumerate(calls) if restore.STAGE_OBJECTS in call)
    database = next(
        i for i, call in enumerate(calls) if any("--single-transaction" in x for x in call)
    )
    smoke = next(i for i, call in enumerate(calls) if restore.SMOKE_OBJECTS in call)
    start = next(i for i, call in enumerate(calls) if "up" in call)
    assert stage < database < smoke < start
    assert result["mode"] == "restored" and result["resumed"] == ["api", "frontend", "worker"]
    assert all("-p" not in call and str(tmp_path / "team.env") in call for call in calls)


def test_success_does_not_start_previously_stopped_applications(tmp_path, monkeypatch, backup):
    calls = docker_fixture(monkeypatch, running="database\napi")
    assert invoke(tmp_path, backup)["resumed"] == ["api"]
    start = next(call for call in calls if "up" in call)
    assert start[-1] == "api" and "frontend" not in start and "worker" not in start


def test_local_verify_autodetects_without_a_team_env_or_production_conversion(
    tmp_path, monkeypatch, backup
):
    calls = docker_fixture(monkeypatch)
    assert restore.restore(tmp_path, backup)["mode"] == "verified"
    assert all(call[call.index("-p") + 1] == "businessaiagents" for call in calls)
    assert all(
        "--env-file" not in call and "stop" not in call and "up" not in call for call in calls
    )


def test_real_staging_and_promotion_preserve_old_files_until_verified(tmp_path, backup):
    root = tmp_path / "objects"
    root.mkdir()
    (root / "previous.txt").write_bytes(b"previous")
    stage, previous = ".restore-stage-fixture", ".restore-previous-fixture"
    with (backup / "document-objects.tar.gz").open("rb") as source:
        subprocess.run(
            [sys.executable, "-c", restore.STAGE_OBJECTS, str(root), stage],
            stdin=source,
            check=True,
        )
    assert (root / "previous.txt").read_bytes() == b"previous"
    assert (root / stage / "nested/source.txt").read_bytes() == b"content"
    subprocess.run(
        [sys.executable, "-c", restore.PROMOTE_OBJECTS, str(root), stage, previous], check=True
    )
    assert (root / previous / "previous.txt").read_bytes() == b"previous"
    assert (root / "nested/source.txt").read_bytes() == b"content"
    assert not (root / stage).exists()
    subprocess.run([sys.executable, "-c", restore.CLEANUP_OBJECTS, str(root), previous], check=True)
    assert not (root / previous).exists()


def test_interrupted_stage_cannot_overwrite_original_tree(tmp_path, backup):
    root = tmp_path / "objects"
    root.mkdir()
    (root / "previous.txt").write_bytes(b"previous")
    (root / ".restore-stage-unfinished").mkdir()
    with (backup / "document-objects.tar.gz").open("rb") as source:
        result = subprocess.run(
            [sys.executable, "-c", restore.STAGE_OBJECTS, str(root), ".restore-stage-next"],
            stdin=source,
            capture_output=True,
        )
    assert result.returncode != 0
    assert (root / "previous.txt").read_bytes() == b"previous"


@pytest.mark.parametrize("change", ["valid", "missing", "corrupted"])
def test_offline_smoke_checks_real_database_object_references(
    client, db, monkeypatch, tmp_path, change
):
    from app.core.config import settings
    from app.main import app
    from app.models import DocumentSourceVersion
    from app.services.documents import get_object_storage
    from app.services.object_storage import LocalObjectStorage

    monkeypatch.setattr(settings, "auth_mode", "disabled")
    storage = LocalObjectStorage(tmp_path, 1024)
    app.dependency_overrides[get_object_storage] = lambda: storage
    created = client.post(
        "/api/v1/documents", files={"file": ("fixture.md", b"synthetic content", "text/markdown")}
    )
    assert created.status_code == 201
    version = db.query(DocumentSourceVersion).one()
    source = tmp_path / version.object_key
    if change == "missing":
        source.unlink()
    elif change == "corrupted":
        source.write_bytes(b"incorrect content")
    monkeypatch.setattr("app.db.SessionLocal", lambda: nullcontext(db))
    monkeypatch.setattr(
        "app.services.graph_invariants.check_graph_invariants",
        lambda _: SimpleNamespace(valid=True),
    )
    monkeypatch.setattr(sys, "argv", ["restore-smoke", str(tmp_path)])
    if change == "valid":
        exec(restore.SMOKE_OBJECTS, {})
    else:
        with pytest.raises((RuntimeError, FileNotFoundError)):
            exec(restore.SMOKE_OBJECTS, {})
