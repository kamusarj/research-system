# Gate C MinIO Attachment Storage

## Current Behavior

Uploaded PDF, Markdown and text objects are stored only in a named local Docker volume. The
database persists opaque object keys, but changing the storage implementation globally would make
existing local objects unreachable.

## Target Behavior

Operators can select an external MinIO/S3-compatible bucket for new attachment writes while existing
plain local keys remain readable. New remote keys carry an explicit `minio://<bucket>/...` scheme so
reads, worker extraction, downloads, duplicate cleanup and rollback route to the correct backend.

## Affected Users

- Operators deploying the Research System outside one local machine.
- Researchers uploading, processing and downloading source documents.

## Affected Product Docs

- `Docs/Research System Completion Plan.md`
- `Docs/Research System Implementation Plan.md`
- `README.md`

## Non-Goals

- No automatic migration or deletion of existing local objects.
- No bundled production MinIO cluster or server lifecycle management.
- No browser-direct presigned uploads in this slice.
- No auth/RBAC or secret-manager implementation.
