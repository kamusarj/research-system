from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from tempfile import TemporaryDirectory

from minio import Minio
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import Base
from app.models import Attachment, AuditEvent, DocumentGraphWorkspace, ResearchItem
from app.services.object_migration import (
    execute_object_migration,
    plan_object_migration,
    verify_object_migration,
)
from app.services.object_storage import LocalObjectStorage, MinioObjectStorage


async def chunks(content: bytes) -> AsyncIterator[bytes]:
    yield content


def secret(value) -> str:
    if value is None or not value.get_secret_value().strip():
        raise RuntimeError("Disposable MinIO proof credentials are not configured")
    return value.get_secret_value().strip()


async def main() -> None:
    content = b"disposable checksummed object migration proof"
    source_key = "documents/proof/source.md"
    digest = hashlib.sha256(content).hexdigest()
    with TemporaryDirectory(prefix="research-object-migration-") as directory:
        engine = create_engine(f"sqlite:///{directory}/proof.db")
        Base.metadata.create_all(engine)
        local = LocalObjectStorage(f"{directory}/objects", 1024)
        await local.put(source_key, chunks(content), {"mime_type": "text/markdown"})
        remote = MinioObjectStorage(
            Minio(
                settings.minio_endpoint,
                access_key=secret(settings.minio_access_key),
                secret_key=secret(settings.minio_secret_key),
                secure=settings.minio_secure,
            ),
            settings.minio_bucket,
            1024,
            auto_create_bucket=True,
            spool_memory_bytes=64 * 1024,
        )
        with Session(engine) as db:
            research = ResearchItem(
                title="Migration proof",
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
            db.add(
                DocumentGraphWorkspace(
                    research_id=research.id,
                    attachment_id=attachment.id,
                    storage_object_key=source_key,
                    content_hash=digest,
                )
            )
            db.commit()

            plan = await plan_object_migration(db, local)
            first = await execute_object_migration(db, local, remote)
            verification = await verify_object_migration(db, local, remote)
            repeated = await execute_object_migration(db, local, remote)
            audit_count = (
                db.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.action == "attachment.object_migrated")
                )
                or 0
            )

    if not plan.clean or len(plan.candidates) != 1:
        raise RuntimeError("Disposable migration plan was not clean")
    if first["migrated_objects"] != 1 or first["deleted_objects"] != 0:
        raise RuntimeError("Disposable object copy did not preserve the source")
    if not verification["clean"] or verification["verified_objects"] != 1:
        raise RuntimeError("Disposable remote/local verification failed")
    if repeated["migrated_objects"] != 0 or audit_count != 1:
        raise RuntimeError("Disposable migration was not idempotent")
    print(
        "OBJECT_MIGRATION_OK",
        json.dumps(
            {
                "planned_objects": len(plan.candidates),
                "migrated_objects": first["migrated_objects"],
                "verified_objects": verification["verified_objects"],
                "verified_bytes": verification["verified_bytes"],
                "local_retained": verification["local_retained"],
                "deleted_objects": first["deleted_objects"],
                "repeat_migrated_objects": repeated["migrated_objects"],
                "audit_events": audit_count,
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
