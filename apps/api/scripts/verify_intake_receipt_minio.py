from __future__ import annotations

import asyncio
import os
import tempfile
from io import BytesIO
from pathlib import Path

from minio import Minio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.datastructures import Headers, UploadFile

from app.core.identity import Principal
from app.db import Base
from app.models import AuditEvent, DocumentGraphWorkspace, IntakeReceiptItem, LinkSubmission
from app.schemas.intake_receipts import ReceiptCreate
from app.services.intake_receipts import (
    deliver_document_item,
    deliver_url_receipt,
    serialize_receipt,
)
from app.services.object_storage import (
    DocumentError,
    LocalObjectStorage,
    MinioObjectStorage,
    RoutedObjectStorage,
)


def upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


def receipt_data(occurrence_ref: str) -> ReceiptCreate:
    return ReceiptCreate.model_validate(
        {
            "source": {
                "type": "api",
                "namespace": "minio-proof",
                "occurrence_ref": occurrence_ref,
                "metadata": {"schema_version": 1, "event_type": "api_request"},
            },
            "items": [],
        }
    )


async def verify() -> None:
    endpoint = os.environ["MINIO_ENDPOINT"]
    access_key = os.environ["MINIO_ACCESS_KEY"]
    secret_key = os.environ["MINIO_SECRET_KEY"]
    bucket = os.environ["MINIO_BUCKET"]
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
    principal = Principal(
        id="proof-operator",
        name="Proof operator",
        email="proof@research.invalid",
        role="owner",
        auth_kind="local",
    )

    with tempfile.TemporaryDirectory(prefix="business-ai-receipt-minio-") as temporary:
        root = Path(temporary)
        engine = create_engine(f"sqlite:///{root / 'proof.db'}")
        Base.metadata.create_all(engine)
        storage = RoutedObjectStorage(
            LocalObjectStorage(root / "local", 2_000_000),
            MinioObjectStorage(
                client,
                bucket,
                2_000_000,
                auto_create_bucket=True,
                spool_memory_bytes=64 * 1024,
            ),
            "minio",
        )
        content = b"%PDF-1.4\nReceipt MinIO durability proof\n%%EOF"
        try:
            with Session(engine) as db:
                first_receipt = deliver_url_receipt(db, receipt_data("proof-event-1"), principal)
                first = await deliver_document_item(
                    db,
                    first_receipt.receipt.id,
                    upload("proof.pdf", content),
                    "attachment-proof-1",
                    storage,
                    principal=principal,
                )
                first_read = serialize_receipt(db, first, principal)
                replay = await deliver_document_item(
                    db,
                    first_receipt.receipt.id,
                    upload("proof.pdf", content),
                    "attachment-proof-1",
                    storage,
                    principal=principal,
                )
                assert serialize_receipt(db, replay, principal).items[0].disposition == "replayed"

                try:
                    await deliver_document_item(
                        db,
                        first_receipt.receipt.id,
                        upload("proof.pdf", b"%PDF-1.4\nConflicting bytes\n%%EOF"),
                        "attachment-proof-1",
                        storage,
                        principal=principal,
                    )
                except DocumentError as exc:
                    assert exc.code == "SOURCE_ITEM_CONFLICT"
                else:
                    raise AssertionError("Conflicting document bytes must be rejected")

                second_receipt = deliver_url_receipt(db, receipt_data("proof-event-2"), principal)
                linked = await deliver_document_item(
                    db,
                    second_receipt.receipt.id,
                    upload("copy.pdf", content),
                    "attachment-proof-2",
                    storage,
                    principal=principal,
                )
                assert serialize_receipt(db, linked, principal).items[0].disposition == (
                    "linked_existing"
                )

                workspaces = list(db.scalars(select(DocumentGraphWorkspace)))
                items = list(db.scalars(select(IntakeReceiptItem)))
                assert len(workspaces) == 1
                assert len(items) == 2
                assert workspaces[0].storage_object_key.startswith(f"minio://{bucket}/")
                downloaded = bytearray()
                async for chunk in storage.open(workspaces[0].storage_object_key):
                    downloaded.extend(chunk)
                assert bytes(downloaded) == content
                assert first_read.items[0].disposition == "queued"
                assert db.query(LinkSubmission).count() == 0
                audit_text = str(
                    [event.payload for event in db.scalars(select(AuditEvent))]
                )
                for forbidden in (
                    "proof-event-1",
                    "attachment-proof-1",
                    "proof.pdf",
                    secret_key,
                ):
                    assert forbidden not in audit_text

            objects = list(client.list_objects(bucket, recursive=True))
            assert len(objects) == 1
            assert not (root / "local").exists() or not list((root / "local").rglob("*"))
            print(
                "INTAKE_RECEIPT_MINIO_OK "
                f"objects={len(objects)} workspaces={len(workspaces)} items={len(items)} "
                f"bytes={len(content)}"
            )
        finally:
            if client.bucket_exists(bucket):
                for item in client.list_objects(bucket, recursive=True):
                    client.remove_object(bucket, item.object_name)
                client.remove_bucket(bucket)
            Base.metadata.drop_all(engine)
            engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify())
