from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Attachment, AuditEvent, DocumentGraphWorkspace
from app.services.object_storage import (
    MINIO_KEY_PREFIX,
    DocumentError,
    LocalObjectStorage,
    MinioObjectStorage,
    _validate_object_name,
)


class ObjectMigrationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ObjectDigest:
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class MigrationCandidate:
    attachment_id: str
    workspace_id: str | None
    source_key: str
    filename: str
    mime_type: str
    digest: ObjectDigest


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    candidates: tuple[MigrationCandidate, ...]
    referenced_objects: int
    legacy_objects: int
    remote_objects: int
    missing_objects: int
    invalid_objects: int
    declared_bytes: int
    verified_bytes: int

    @property
    def clean(self) -> bool:
        return self.missing_objects == 0 and self.invalid_objects == 0

    def report(self) -> dict[str, int | bool | str]:
        return {
            "mode": "plan",
            "referenced_objects": self.referenced_objects,
            "legacy_objects": self.legacy_objects,
            "remote_objects": self.remote_objects,
            "eligible_objects": len(self.candidates),
            "missing_objects": self.missing_objects,
            "invalid_objects": self.invalid_objects,
            "declared_bytes": self.declared_bytes,
            "verified_bytes": self.verified_bytes,
            "clean": self.clean,
        }


async def _digest(stream: AsyncIterator[bytes], max_bytes: int) -> ObjectDigest:
    digest = hashlib.sha256()
    size = 0
    async for chunk in stream:
        if not chunk:
            continue
        size += len(chunk)
        if size > max_bytes:
            raise ObjectMigrationError(
                "OBJECT_MIGRATION_INVALID",
                "A referenced object exceeds the configured document limit.",
            )
        digest.update(chunk)
    if size == 0:
        raise ObjectMigrationError(
            "OBJECT_MIGRATION_INVALID", "A referenced object is empty."
        )
    return ObjectDigest(size_bytes=size, sha256=digest.hexdigest())


def _workspace_map(db: Session) -> dict[str, DocumentGraphWorkspace]:
    return {
        workspace.attachment_id: workspace
        for workspace in db.scalars(select(DocumentGraphWorkspace))
    }


async def plan_object_migration(db: Session, local: LocalObjectStorage) -> MigrationPlan:
    attachments = list(db.scalars(select(Attachment).order_by(Attachment.id)))
    workspaces = _workspace_map(db)
    candidates: list[MigrationCandidate] = []
    legacy_objects = 0
    remote_objects = 0
    missing_objects = 0
    invalid_objects = 0
    declared_bytes = 0
    verified_bytes = 0

    for attachment in attachments:
        workspace = workspaces.get(attachment.id)
        if workspace is not None and workspace.storage_object_key != attachment.object_key:
            invalid_objects += 1
            continue
        if attachment.object_key.startswith(MINIO_KEY_PREFIX):
            remote_objects += 1
            continue
        legacy_objects += 1
        declared_bytes += attachment.size_bytes
        if "://" in attachment.object_key:
            invalid_objects += 1
            continue
        try:
            source_key = _validate_object_name(attachment.object_key)
            digest = await _digest(local.open(source_key), local.max_bytes)
        except DocumentError as exc:
            if exc.status_code == 404:
                missing_objects += 1
            else:
                invalid_objects += 1
            continue
        except ObjectMigrationError:
            invalid_objects += 1
            continue
        if digest.size_bytes != attachment.size_bytes or (
            workspace is not None and workspace.content_hash != digest.sha256
        ):
            invalid_objects += 1
            continue
        verified_bytes += digest.size_bytes
        candidates.append(
            MigrationCandidate(
                attachment_id=attachment.id,
                workspace_id=workspace.id if workspace is not None else None,
                source_key=source_key,
                filename=attachment.filename,
                mime_type=attachment.mime_type,
                digest=digest,
            )
        )

    return MigrationPlan(
        candidates=tuple(candidates),
        referenced_objects=len(attachments),
        legacy_objects=legacy_objects,
        remote_objects=remote_objects,
        missing_objects=missing_objects,
        invalid_objects=invalid_objects,
        declared_bytes=declared_bytes,
        verified_bytes=verified_bytes,
    )


def _assert_digest(actual: ObjectDigest, expected: ObjectDigest) -> None:
    if actual != expected:
        raise ObjectMigrationError(
            "OBJECT_MIGRATION_CHECKSUM_MISMATCH",
            "Object size or checksum verification failed.",
        )


async def execute_object_migration(
    db: Session,
    local: LocalObjectStorage,
    remote: MinioObjectStorage,
) -> dict[str, int | bool | str]:
    plan = await plan_object_migration(db, local)
    if not plan.clean:
        raise ObjectMigrationError(
            "OBJECT_MIGRATION_PLAN_INVALID",
            "The complete legacy object inventory must be valid before execution.",
        )

    migrated = 0
    migrated_bytes = 0
    for candidate in plan.candidates:
        try:
            attachment = db.scalar(
                select(Attachment)
                .where(Attachment.id == candidate.attachment_id)
                .with_for_update()
            )
            if attachment is None:
                raise ObjectMigrationError(
                    "OBJECT_MIGRATION_REFERENCE_CHANGED",
                    "An object reference changed after planning.",
                )
            if attachment.object_key.startswith(MINIO_KEY_PREFIX):
                db.rollback()
                continue
            if attachment.object_key != candidate.source_key:
                raise ObjectMigrationError(
                    "OBJECT_MIGRATION_REFERENCE_CHANGED",
                    "An object reference changed after planning.",
                )
            workspace = (
                db.scalar(
                    select(DocumentGraphWorkspace)
                    .where(DocumentGraphWorkspace.id == candidate.workspace_id)
                    .with_for_update()
                )
                if candidate.workspace_id is not None
                else None
            )
            if candidate.workspace_id is not None and (
                workspace is None or workspace.storage_object_key != candidate.source_key
            ):
                raise ObjectMigrationError(
                    "OBJECT_MIGRATION_REFERENCE_CHANGED",
                    "An object reference changed after planning.",
                )

            stored = await remote.put(
                candidate.source_key,
                local.open(candidate.source_key),
                {"filename": candidate.filename, "mime_type": candidate.mime_type},
            )
            uploaded = ObjectDigest(stored.size_bytes, stored.sha256)
            _assert_digest(uploaded, candidate.digest)
            _assert_digest(
                await _digest(remote.open(stored.key), remote.max_bytes), candidate.digest
            )
            _assert_digest(
                await _digest(local.open(candidate.source_key), local.max_bytes),
                candidate.digest,
            )

            attachment.object_key = stored.key
            if workspace is not None:
                workspace.storage_object_key = stored.key
            db.add(
                AuditEvent(
                    entity_type="attachment",
                    entity_id=attachment.id,
                    action="attachment.object_migrated",
                    actor="operator-cli",
                    payload={
                        "source_key_sha256": hashlib.sha256(
                            candidate.source_key.encode("utf-8")
                        ).hexdigest(),
                        "content_sha256": candidate.digest.sha256,
                        "size_bytes": candidate.digest.size_bytes,
                        "workspace_backed": workspace is not None,
                        "target_backend": "minio",
                        "target_bucket": remote.bucket,
                    },
                )
            )
            db.commit()
        except (DocumentError, ObjectMigrationError):
            db.rollback()
            raise
        except SQLAlchemyError as exc:
            db.rollback()
            raise ObjectMigrationError(
                "OBJECT_MIGRATION_DATABASE_FAILED",
                "The verified object reference could not be committed.",
            ) from exc
        migrated += 1
        migrated_bytes += candidate.digest.size_bytes

    return {
        "mode": "execute",
        "planned_objects": len(plan.candidates),
        "migrated_objects": migrated,
        "migrated_bytes": migrated_bytes,
        "remote_verified": migrated,
        "local_retained": migrated,
        "deleted_objects": 0,
        "clean": True,
    }


async def verify_object_migration(
    db: Session,
    local: LocalObjectStorage,
    remote: MinioObjectStorage,
) -> dict[str, int | bool | str]:
    migrated_ids = set(
        db.scalars(
            select(AuditEvent.entity_id).where(
                AuditEvent.entity_type == "attachment",
                AuditEvent.action == "attachment.object_migrated",
            )
        )
    )
    attachments = list(
        db.scalars(
            select(Attachment)
            .where(Attachment.id.in_(migrated_ids))
            .order_by(Attachment.id)
        )
    )
    workspaces = _workspace_map(db)
    prefix = f"{MINIO_KEY_PREFIX}{remote.bucket}/"
    remote_objects = 0
    verified_objects = 0
    verified_bytes = 0
    missing_objects = 0
    invalid_objects = 0

    for attachment in attachments:
        if not attachment.object_key.startswith(MINIO_KEY_PREFIX):
            continue
        remote_objects += 1
        workspace = workspaces.get(attachment.id)
        if (
            not attachment.object_key.startswith(prefix)
            or (workspace is not None and workspace.storage_object_key != attachment.object_key)
        ):
            invalid_objects += 1
            continue
        source_key = attachment.object_key[len(prefix) :]
        try:
            source_key = _validate_object_name(source_key)
            local_digest = await _digest(local.open(source_key), local.max_bytes)
            remote_digest = await _digest(
                remote.open(attachment.object_key), remote.max_bytes
            )
        except DocumentError as exc:
            if exc.status_code == 404:
                missing_objects += 1
            else:
                invalid_objects += 1
            continue
        except ObjectMigrationError:
            invalid_objects += 1
            continue
        if (
            local_digest != remote_digest
            or local_digest.size_bytes != attachment.size_bytes
            or (workspace is not None and workspace.content_hash != local_digest.sha256)
        ):
            invalid_objects += 1
            continue
        verified_objects += 1
        verified_bytes += local_digest.size_bytes

    clean = missing_objects == 0 and invalid_objects == 0
    return {
        "mode": "verify",
        "remote_objects": remote_objects,
        "verified_objects": verified_objects,
        "verified_bytes": verified_bytes,
        "missing_objects": missing_objects,
        "invalid_objects": invalid_objects,
        "local_retained": verified_objects,
        "clean": clean,
    }
