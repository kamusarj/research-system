import asyncio
import hashlib
import json
import sys

import pytest
from sqlalchemy import func, select
from test_object_storage import FakeMinioClient, chunks, read_all, remote_storage

from app.models import Attachment, AuditEvent, DocumentGraphWorkspace, ResearchItem
from app.services.object_migration import (
    ObjectMigrationError,
    execute_object_migration,
    plan_object_migration,
    verify_object_migration,
)
from app.services.object_storage import LocalObjectStorage


def seeded_object(db, tmp_path, content=b"verified legacy document"):
    source_key = "documents/workspace/source.md"
    digest = hashlib.sha256(content).hexdigest()
    local = LocalObjectStorage(tmp_path, 1024)
    asyncio.run(local.put(source_key, chunks(content), {"mime_type": "text/markdown"}))
    research = ResearchItem(
        title="Legacy upload",
        type="reference",
        status="draft",
        collection_method="upload",
        content="",
        authors=[],
    )
    db.add(research)
    db.flush()
    attachment = Attachment(
        research_id=research.id,
        filename="source.md",
        object_key=source_key,
        mime_type="text/markdown",
        size_bytes=len(content),
    )
    db.add(attachment)
    db.flush()
    workspace = DocumentGraphWorkspace(
        research_id=research.id,
        attachment_id=attachment.id,
        storage_object_key=source_key,
        content_hash=digest,
    )
    db.add(workspace)
    db.commit()
    return local, attachment.id, workspace.id, source_key, content


def test_object_migration_plan_is_read_only_and_emits_only_aggregates(db, tmp_path):
    local, attachment_id, _workspace_id, source_key, content = seeded_object(db, tmp_path)

    plan = asyncio.run(plan_object_migration(db, local))
    report = plan.report()

    assert report == {
        "mode": "plan",
        "referenced_objects": 1,
        "legacy_objects": 1,
        "remote_objects": 0,
        "eligible_objects": 1,
        "missing_objects": 0,
        "invalid_objects": 0,
        "declared_bytes": len(content),
        "verified_bytes": len(content),
        "clean": True,
    }
    serialized = json.dumps(report)
    assert source_key not in serialized
    assert attachment_id not in serialized
    assert db.get(Attachment, attachment_id).object_key == source_key
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_execute_copies_verifies_updates_audits_and_repeats_safely(db, tmp_path):
    local, attachment_id, workspace_id, source_key, content = seeded_object(db, tmp_path)
    client = FakeMinioClient()
    remote = remote_storage(client)

    first = asyncio.run(execute_object_migration(db, local, remote))
    db.expire_all()
    attachment = db.get(Attachment, attachment_id)
    workspace = db.get(DocumentGraphWorkspace, workspace_id)
    audit = db.scalar(
        select(AuditEvent).where(AuditEvent.action == "attachment.object_migrated")
    )

    assert first == {
        "mode": "execute",
        "planned_objects": 1,
        "migrated_objects": 1,
        "migrated_bytes": len(content),
        "remote_verified": 1,
        "local_retained": 1,
        "deleted_objects": 0,
        "clean": True,
    }
    assert attachment.object_key == workspace.storage_object_key
    assert attachment.object_key.startswith("minio://research-documents/")
    assert asyncio.run(read_all(local, source_key)) == content
    assert asyncio.run(read_all(remote, attachment.object_key)) == content
    assert audit.actor == "operator-cli"
    assert audit.payload["content_sha256"] == hashlib.sha256(content).hexdigest()
    assert source_key not in json.dumps(audit.payload)

    verification = asyncio.run(verify_object_migration(db, local, remote))
    repeated = asyncio.run(execute_object_migration(db, local, remote))

    assert verification["clean"] is True
    assert verification["verified_objects"] == 1
    assert verification["local_retained"] == 1
    assert repeated["planned_objects"] == 0
    assert repeated["migrated_objects"] == 0
    assert db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.action == "attachment.object_migrated")
    ) == 1


@pytest.mark.parametrize("problem", ["missing", "size", "hash", "reference"])
def test_execute_refuses_incomplete_or_inconsistent_inventory(db, tmp_path, problem):
    local, attachment_id, workspace_id, source_key, _content = seeded_object(db, tmp_path)
    attachment = db.get(Attachment, attachment_id)
    workspace = db.get(DocumentGraphWorkspace, workspace_id)
    if problem == "missing":
        asyncio.run(local.delete(source_key))
    elif problem == "size":
        attachment.size_bytes += 1
    elif problem == "hash":
        workspace.content_hash = "0" * 64
    else:
        workspace.storage_object_key = "documents/other/source.md"
    db.commit()
    client = FakeMinioClient()
    remote = remote_storage(client)

    plan = asyncio.run(plan_object_migration(db, local))
    with pytest.raises(ObjectMigrationError) as caught:
        asyncio.run(execute_object_migration(db, local, remote))

    assert caught.value.code == "OBJECT_MIGRATION_PLAN_INVALID"
    assert plan.clean is False
    assert client.objects == {}
    db.expire_all()
    assert db.get(Attachment, attachment_id).object_key == source_key
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_verify_detects_remote_corruption_without_mutating_references(db, tmp_path):
    local, attachment_id, _workspace_id, _source_key, _content = seeded_object(db, tmp_path)
    client = FakeMinioClient()
    remote = remote_storage(client)
    asyncio.run(execute_object_migration(db, local, remote))
    db.expire_all()
    target_key = db.get(Attachment, attachment_id).object_key
    object_name = target_key.removeprefix("minio://research-documents/")
    client.objects[("research-documents", object_name)] = b"corrupt"

    report = asyncio.run(verify_object_migration(db, local, remote))

    assert report["clean"] is False
    assert report["invalid_objects"] == 1
    assert report["verified_objects"] == 0
    assert db.get(Attachment, attachment_id).object_key == target_key


def test_verify_excludes_remote_native_objects_without_migration_audit(db, tmp_path):
    _local, attachment_id, workspace_id, _source_key, _content = seeded_object(db, tmp_path)
    target_key = "minio://research-documents/documents/native/source.md"
    db.get(Attachment, attachment_id).object_key = target_key
    db.get(DocumentGraphWorkspace, workspace_id).storage_object_key = target_key
    db.commit()
    client = FakeMinioClient()
    remote = remote_storage(client)

    report = asyncio.run(
        verify_object_migration(db, LocalObjectStorage(tmp_path, 1024), remote)
    )

    assert report["remote_objects"] == 0
    assert report["verified_objects"] == 0
    assert report["clean"] is True


def test_execute_cli_requires_explicit_copy_only_confirmation(monkeypatch):
    from app import operations

    monkeypatch.setattr(
        sys,
        "argv",
        ["operations", "migrate-objects", "--mode", "execute"],
    )

    with pytest.raises(SystemExit, match="confirm-copy-only"):
        operations.main()
