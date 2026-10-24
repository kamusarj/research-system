# Validation

## Proof Strategy

Use an injected MinIO client double for boundary/failure tests, existing upload/download tests for
local compatibility, the full backend suite for regression, and a disposable non-LAN MinIO container
for a real put/open/delete round trip. Do not claim production MinIO operations proof from the
disposable single-node fixture.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Key validation, max size/hash, bucket provisioning policy, safe error mapping, response cleanup. |
| Integration | Routed local legacy read plus MinIO write/read/delete; existing document workflow unchanged. |
| E2E | Existing document upload/download/processing UI remains green. |
| Platform | Settings/config validate; API and worker images contain the pinned SDK; disposable real round trip. |
| Performance | Upload spools with a bounded memory threshold and streams downloads in chunks. |
| Logs/Audit | No credentials, bytes or upstream error bodies in API responses/logs. |

## Fixtures

- Fake MinIO client with deterministic buckets, objects and typed failures.
- Temporary local directory for legacy objects.
- Disposable isolated MinIO server with non-production credentials and no host/LAN port.

## Commands

```text
cd apps/api && uv run --frozen python -m pytest -q tests/test_object_storage.py tests/test_documents.py
cd apps/api && uv run --frozen python -m pytest -q
cd apps/api && .venv/bin/ruff check app tests
docker compose build api worker
```

## Acceptance Evidence

- MinIO SDK `7.2.20` is locked in `uv.lock`; API and worker images build with the dependency.
- Seven storage-boundary tests cover scheme keys, hash/size, streamed reads and response cleanup,
  pre-provisioned bucket policy, safe upstream error mapping, local/remote rollback routing and
  credential-pair validation.
- Document processing schedules bounded retry after a transient storage HTTP 503. Existing local
  upload/download, duplicate and processing cases remain green.
- All 96 backend tests and Ruff pass; the only backend warning is the known Starlette/httpx
  TestClient deprecation. All 27 Playwright desktop/tablet/mobile cases pass.
- A disposable MinIO server on the internal Docker network with tmpfs and no published port passed
  real put → streamed open → delete for a 32-byte object; the container was removed afterward. This
  is integration proof, not a production topology claim.
- Rebuilt local runtime passed upload/download for workspace
  `32494694-4e0f-4b80-9086-3d78143672b5` with a plain legacy/local key. Direct/proxied health and
  readiness remain healthy with valid canonical graph invariants.
