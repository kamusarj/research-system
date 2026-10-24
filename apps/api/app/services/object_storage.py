import asyncio
import hashlib
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Protocol

from minio import Minio
from minio.error import S3Error

MINIO_KEY_PREFIX = "minio://"
MINIO_NOT_FOUND_CODES = {"NoSuchBucket", "NoSuchKey", "NoSuchObject", "XMinioInvalidObjectName"}


class DocumentError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    size_bytes: int
    sha256: str
    metadata: dict[str, str]


class ObjectStorage(Protocol):
    async def put(
        self, key: str, stream: AsyncIterator[bytes], metadata: dict[str, str]
    ) -> StoredObject: ...

    async def open(self, key: str) -> AsyncIterator[bytes]: ...

    async def delete(self, key: str) -> None: ...


class LocalObjectStorage:
    def __init__(self, root: str | Path, max_bytes: int):
        self.root = Path(root).resolve()
        self.max_bytes = max_bytes

    def _path(self, key: str) -> Path:
        if not key or Path(key).is_absolute():
            raise DocumentError("DOCUMENT_STORAGE_FAILED", "Invalid object key", 500)
        target = (self.root / key).resolve()
        if not target.is_relative_to(self.root):
            raise DocumentError("DOCUMENT_STORAGE_FAILED", "Invalid object key", 500)
        return target

    async def put(
        self, key: str, stream: AsyncIterator[bytes], metadata: dict[str, str]
    ) -> StoredObject:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.upload")
        size = 0
        digest = hashlib.sha256()
        try:
            with temporary.open("xb") as output:
                async for chunk in stream:
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise DocumentError(
                            "DOCUMENT_TOO_LARGE",
                            f"Document exceeds the {self.max_bytes}-byte upload limit",
                            413,
                        )
                    digest.update(chunk)
                    output.write(chunk)
            if size == 0:
                raise DocumentError("DOCUMENT_EMPTY", "Uploaded document is empty")
            os.replace(temporary, target)
        except DocumentError:
            temporary.unlink(missing_ok=True)
            raise
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "Unable to store the uploaded document", 500
            ) from exc
        return StoredObject(
            key=key,
            size_bytes=size,
            sha256=digest.hexdigest(),
            metadata=metadata,
        )

    async def open(self, key: str) -> AsyncIterator[bytes]:
        target = self._path(key)
        try:
            with target.open("rb") as source:
                while chunk := source.read(64 * 1024):
                    yield chunk
        except OSError as exc:
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "Stored document is unavailable", 404
            ) from exc

    async def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError as exc:
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "Unable to delete the stored document", 500
            ) from exc


def _validate_object_name(key: str) -> str:
    if not key or key.startswith(("/", MINIO_KEY_PREFIX)):
        raise DocumentError("DOCUMENT_STORAGE_FAILED", "Invalid object key", 500)
    parts = key.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise DocumentError("DOCUMENT_STORAGE_FAILED", "Invalid object key", 500)
    return key


class MinioObjectStorage:
    def __init__(
        self,
        client: Minio,
        bucket: str,
        max_bytes: int,
        *,
        auto_create_bucket: bool = False,
        spool_memory_bytes: int = 8_388_608,
    ):
        if not bucket or "/" in bucket:
            raise DocumentError("DOCUMENT_STORAGE_FAILED", "Invalid object storage bucket", 500)
        self.client = client
        self.bucket = bucket
        self.max_bytes = max_bytes
        self.auto_create_bucket = auto_create_bucket
        self.spool_memory_bytes = max(64 * 1024, min(spool_memory_bytes, max_bytes))

    def _stored_key(self, object_name: str) -> str:
        return f"{MINIO_KEY_PREFIX}{self.bucket}/{object_name}"

    def _object_name(self, stored_key: str) -> str:
        prefix = f"{MINIO_KEY_PREFIX}{self.bucket}/"
        if not stored_key.startswith(prefix):
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED",
                "Stored object does not belong to the configured bucket",
                500,
            )
        return _validate_object_name(stored_key[len(prefix) :])

    def _ensure_bucket(self) -> None:
        if self.client.bucket_exists(self.bucket):
            return
        if not self.auto_create_bucket:
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED",
                "The configured object storage bucket is unavailable",
                503,
            )
        try:
            self.client.make_bucket(self.bucket)
        except S3Error as exc:
            if exc.code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
                raise

    @staticmethod
    def _error(exc: Exception, action: str) -> DocumentError:
        if isinstance(exc, DocumentError):
            return exc
        if isinstance(exc, S3Error) and exc.code in MINIO_NOT_FOUND_CODES:
            return DocumentError(
                "DOCUMENT_STORAGE_FAILED", "Stored document is unavailable", 404
            )
        messages = {
            "store": "Unable to store the uploaded document",
            "open": "Stored document is unavailable",
            "delete": "Unable to delete the stored document",
        }
        return DocumentError("DOCUMENT_STORAGE_FAILED", messages[action], 503)

    async def put(
        self, key: str, stream: AsyncIterator[bytes], metadata: dict[str, str]
    ) -> StoredObject:
        object_name = _validate_object_name(key)
        size = 0
        digest = hashlib.sha256()
        with SpooledTemporaryFile(max_size=self.spool_memory_bytes, mode="w+b") as temporary:
            async for chunk in stream:
                if not chunk:
                    continue
                size += len(chunk)
                if size > self.max_bytes:
                    raise DocumentError(
                        "DOCUMENT_TOO_LARGE",
                        f"Document exceeds the {self.max_bytes}-byte upload limit",
                        413,
                    )
                digest.update(chunk)
                temporary.write(chunk)
            if size == 0:
                raise DocumentError("DOCUMENT_EMPTY", "Uploaded document is empty")
            temporary.seek(0)
            try:
                await asyncio.to_thread(self._ensure_bucket)
                await asyncio.to_thread(
                    self.client.put_object,
                    self.bucket,
                    object_name,
                    temporary,
                    size,
                    content_type=metadata.get("mime_type", "application/octet-stream"),
                    metadata={"sha256": digest.hexdigest()},
                )
            except DocumentError:
                raise
            except Exception as exc:
                raise self._error(exc, "store") from exc
        return StoredObject(
            key=self._stored_key(object_name),
            size_bytes=size,
            sha256=digest.hexdigest(),
            metadata=metadata,
        )

    async def open(self, key: str) -> AsyncIterator[bytes]:
        object_name = self._object_name(key)
        try:
            response = await asyncio.to_thread(
                self.client.get_object, self.bucket, object_name
            )
        except Exception as exc:
            raise self._error(exc, "open") from exc
        try:
            while chunk := await asyncio.to_thread(response.read, 64 * 1024):
                yield chunk
        except Exception as exc:
            raise self._error(exc, "open") from exc
        finally:
            with suppress(Exception):
                await asyncio.to_thread(response.close)
            with suppress(Exception):
                await asyncio.to_thread(response.release_conn)

    async def delete(self, key: str) -> None:
        object_name = self._object_name(key)
        try:
            await asyncio.to_thread(self.client.remove_object, self.bucket, object_name)
        except Exception as exc:
            raise self._error(exc, "delete") from exc


class RoutedObjectStorage:
    def __init__(
        self,
        local: LocalObjectStorage,
        minio: MinioObjectStorage | None,
        write_backend: str,
    ):
        if write_backend not in {"local", "minio"}:
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "Unsupported document storage backend", 500
            )
        if write_backend == "minio" and minio is None:
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "MinIO storage credentials are not configured", 503
            )
        self.local = local
        self.minio = minio
        self.write_backend = write_backend

    def _remote(self) -> MinioObjectStorage:
        if self.minio is None:
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "MinIO storage credentials are not configured", 503
            )
        return self.minio

    async def put(
        self, key: str, stream: AsyncIterator[bytes], metadata: dict[str, str]
    ) -> StoredObject:
        if self.write_backend == "minio":
            return await self._remote().put(key, stream, metadata)
        return await self.local.put(key, stream, metadata)

    async def open(self, key: str) -> AsyncIterator[bytes]:
        storage: ObjectStorage = self._remote() if key.startswith(MINIO_KEY_PREFIX) else self.local
        async for chunk in storage.open(key):
            yield chunk

    async def delete(self, key: str) -> None:
        storage: ObjectStorage = self._remote() if key.startswith(MINIO_KEY_PREFIX) else self.local
        await storage.delete(key)
