# Design

## Domain Model

`Attachment.object_key` and `DocumentGraphWorkspace.storage_object_key` remain opaque durable
references. Existing keys without a scheme mean local storage. New MinIO objects use
`minio://<configured-bucket>/<object-name>`; the configured bucket must match on every read/delete.

## Application Flow

1. `get_object_storage` builds a routed store from typed settings.
2. Uploads write to the selected backend, still enforcing the server-owned byte limit and SHA-256.
3. Local writes retain the current plain key. MinIO writes return the scheme-qualified key.
4. Reads/deletes route scheme-qualified keys to MinIO and legacy plain keys to local storage.
5. Worker extraction and authorized API downloads continue through the same `ObjectStorage` contract.
6. Missing credentials, wrong bucket, unavailable service and missing objects map to safe typed
   `DOCUMENT_STORAGE_FAILED` errors without exposing endpoint credentials.

## Interface Contract

No public route or response shape changes. Generated document-workspace storage keys and credentials
remain server-only.

## Data Model

No migration. Existing opaque key columns already have sufficient length. The scheme becomes part of
the storage-reference contract, and plain keys remain permanently defined as legacy/local.

## UI / Platform Impact

No UI change. Local storage remains the default. Production deployments supply an external endpoint,
bucket and credentials; switching the write backend does not move historical objects.

## Observability

Log backend operation, bucket and object-key hash or workspace identifier when needed; never log
access keys, secret keys, uploaded bytes or presigned URLs. Health/readiness remains separate from
object-storage probing so an unavailable bucket does not expose secrets or block unrelated reads.

## Alternatives Considered

1. A global backend switch with unchanged keys was rejected because historical local objects would
   become unreachable.
2. A database migration adding backend columns was rejected for this additive slice because opaque
   scheme-qualified keys preserve routing without duplicating state across attachment/workspace rows.
3. Bundling an outdated MinIO server image was rejected; production server lifecycle and security
   patching belong to deployment infrastructure, not the application repository.
