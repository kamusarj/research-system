import asyncio
import io
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.services.documents import build_object_storage
from app.services.object_storage import (
    DocumentError,
    LocalObjectStorage,
    MinioObjectStorage,
    RoutedObjectStorage,
)


async def chunks(*items: bytes):
    for item in items:
        yield item


async def read_all(storage, key: str) -> bytes:
    return b"".join([chunk async for chunk in storage.open(key)])


class FakeResponse(io.BytesIO):
    def __init__(self, content: bytes):
        super().__init__(content)
        self.closed_by_client = False
        self.released = False

    def close(self):
        self.closed_by_client = True
        super().close()

    def release_conn(self):
        self.released = True


class FakeMinioClient:
    def __init__(self):
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}
        self.responses: list[FakeResponse] = []
        self.fail_put = False

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(self, bucket, key, source, length, **_kwargs):
        if self.fail_put:
            raise RuntimeError("upstream credential detail must not escape")
        self.objects[(bucket, key)] = source.read(length)

    def get_object(self, bucket: str, key: str):
        response = FakeResponse(self.objects[(bucket, key)])
        self.responses.append(response)
        return response

    def remove_object(self, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)


def remote_storage(client: FakeMinioClient, **kwargs) -> MinioObjectStorage:
    return MinioObjectStorage(
        client,
        "research-documents",
        kwargs.pop("max_bytes", 1024),
        auto_create_bucket=kwargs.pop("auto_create_bucket", True),
        spool_memory_bytes=kwargs.pop("spool_memory_bytes", 64),
        **kwargs,
    )


def test_minio_put_open_delete_round_trip_uses_scheme_and_closes_response():
    client = FakeMinioClient()
    storage = remote_storage(client)

    stored = asyncio.run(
        storage.put(
            "documents/workspace/source.md",
            chunks(b"governed ", b"agent"),
            {"mime_type": "text/markdown"},
        )
    )

    assert stored.key == "minio://research-documents/documents/workspace/source.md"
    assert stored.size_bytes == 14
    assert len(stored.sha256) == 64
    assert asyncio.run(read_all(storage, stored.key)) == b"governed agent"
    assert client.responses[0].closed_by_client is True
    assert client.responses[0].released is True

    asyncio.run(storage.delete(stored.key))
    assert client.objects == {}


def test_minio_enforces_size_before_network_upload():
    client = FakeMinioClient()
    storage = remote_storage(client, max_bytes=3)

    with pytest.raises(DocumentError) as caught:
        asyncio.run(storage.put("documents/large.txt", chunks(b"1234"), {}))

    assert caught.value.code == "DOCUMENT_TOO_LARGE"
    assert caught.value.status_code == 413
    assert client.objects == {}


def test_minio_requires_preprovisioned_bucket_unless_explicitly_enabled():
    client = FakeMinioClient()
    storage = remote_storage(client, auto_create_bucket=False)

    with pytest.raises(DocumentError) as caught:
        asyncio.run(storage.put("documents/source.txt", chunks(b"content"), {}))

    assert caught.value.status_code == 503
    assert client.buckets == set()


def test_minio_maps_upstream_failure_without_leaking_details():
    client = FakeMinioClient()
    client.buckets.add("research-documents")
    client.fail_put = True
    storage = remote_storage(client, auto_create_bucket=False)

    with pytest.raises(DocumentError) as caught:
        asyncio.run(storage.put("documents/source.txt", chunks(b"content"), {}))

    assert caught.value.code == "DOCUMENT_STORAGE_FAILED"
    assert caught.value.status_code == 503
    assert caught.value.message == "Unable to store the uploaded document"
    assert "credential" not in caught.value.message


def test_routed_storage_preserves_legacy_local_reads_and_remote_rollback(tmp_path):
    local = LocalObjectStorage(tmp_path, 1024)
    client = FakeMinioClient()
    remote = remote_storage(client)
    remote_writes = RoutedObjectStorage(local, remote, "minio")
    local_writes = RoutedObjectStorage(local, remote, "local")

    legacy = asyncio.run(local.put("documents/legacy.txt", chunks(b"legacy"), {}))
    current = asyncio.run(
        remote_writes.put("documents/current.txt", chunks(b"remote"), {})
    )

    assert asyncio.run(read_all(remote_writes, legacy.key)) == b"legacy"
    assert asyncio.run(read_all(remote_writes, current.key)) == b"remote"
    rolled_back = asyncio.run(
        local_writes.put("documents/after-rollback.txt", chunks(b"local again"), {})
    )
    assert not rolled_back.key.startswith("minio://")
    assert asyncio.run(read_all(local_writes, current.key)) == b"remote"


def test_remote_key_must_match_configured_bucket():
    storage = remote_storage(FakeMinioClient())

    with pytest.raises(DocumentError) as caught:
        asyncio.run(read_all(storage, "minio://other-bucket/documents/source.txt"))

    assert caught.value.code == "DOCUMENT_STORAGE_FAILED"
    assert "configured bucket" in caught.value.message


def test_storage_factory_requires_minio_credentials_as_a_pair(tmp_path):
    config = SimpleNamespace(
        document_storage_dir=str(tmp_path),
        document_max_upload_bytes=1024,
        document_storage_backend="local",
        minio_access_key=SecretStr("access-only"),
        minio_secret_key=None,
        minio_endpoint="minio:9000",
        minio_secure=False,
        minio_region=None,
        minio_bucket="research-documents",
        minio_auto_create_bucket=False,
        minio_spool_memory_bytes=64,
    )

    with pytest.raises(DocumentError) as caught:
        build_object_storage(config)

    assert caught.value.status_code == 503
    assert "together" in caught.value.message
