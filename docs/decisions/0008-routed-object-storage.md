# 0008 Routed Object Storage

Date: 2026-07-21

## Status

Accepted

## Context

Gate C requires MinIO binary attachments, while the running system already has durable attachment
rows pointing to plain keys in a local named volume. A global backend switch would reinterpret those
keys as MinIO objects and make historical content unavailable.

## Decision

Keep object keys opaque and route them by scheme. Plain keys permanently mean local storage;
new remote writes use `minio://<configured-bucket>/<object-name>`. The configured write backend is
reversible, and reads/deletes continue to support both key forms. No object is migrated or deleted
automatically. Production MinIO service provisioning, encryption policy and credentials are external
deployment responsibilities.

## Alternatives Considered

1. Globally reinterpret every key using the active backend: rejected because rollback and historical
   reads are unsafe.
2. Add backend columns to both attachment and workspace tables: deferred because it duplicates an
   already opaque reference and requires migration without improving this two-backend contract.
3. Bundle a MinIO server in core Compose: rejected because production lifecycle, patching and
   topology are infrastructure choices; local integration uses only a disposable isolated fixture.

## Consequences

Positive:

- Existing local objects remain readable after remote writes are enabled.
- Backend selection can roll back without rewriting database rows.
- Public document upload/download APIs remain unchanged; generated workspace keys and storage
  credentials stay server-only.

Tradeoffs:

- Operators must retain the local object volume until its historical objects are explicitly migrated.
- A deployment that has remote-key rows still needs MinIO read credentials even when new writes have
  been rolled back to local.
- Multi-bucket routing is intentionally not supported in this slice.

## Follow-Up

- Add a separately authorized, checksummed migration command before removing any legacy volume.
- Define managed secret deployment and external MinIO encryption/backup requirements in Gate C.
