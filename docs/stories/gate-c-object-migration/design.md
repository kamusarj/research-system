# Design

## Domain Model

An object migration candidate is one plain-key `Attachment` plus its optional
`DocumentGraphWorkspace`. A workspace-backed candidate is valid only when both rows reference the
same key, the local byte count matches `Attachment.size_bytes`, and the local SHA-256 matches
`DocumentGraphWorkspace.content_hash`. A metadata-only attachment may migrate only when its local
object exists and matches its declared size.

The source key remains the MinIO object name, so a migrated reference is deterministic:
`minio://<configured-bucket>/<source-key>`. Local bytes are immutable source evidence throughout the
operation and are never removed by application code.

## Application Flow

1. `plan` selects plain-key attachments, validates key syntax/reference consistency and streams each
   local object to compute its byte count and SHA-256.
2. Invalid/missing candidates are counted without printing paths, IDs, filenames or content.
3. `execute` requires `--confirm-copy-only`, refuses to start if the complete plan is not clean and
   processes one candidate at a time.
4. For each candidate, lock/recheck its current references, stream local bytes to MinIO, stream the
   remote copy back, compare size/SHA-256, verify the local source again, update both references and
   append an audit event in one PostgreSQL transaction.
5. Each commit makes the operation resumable. An external object copied before an interruption is
   harmless: a retry overwrites it from the still-canonical local source and re-verifies it.
6. `verify` checks migrated references in the configured bucket against both remote and retained
   local bytes. It reports aggregate counts only.

## Interface Contract

```text
python -m app.operations migrate-objects --mode plan
python -m app.operations migrate-objects --mode execute --confirm-copy-only
python -m app.operations migrate-objects --mode verify
```

The command emits one JSON summary containing mode, aggregate reference/object counts, byte totals,
invalid/missing counts and checksum outcomes. Typed failures go to stderr without raw keys, object
paths, filenames, provider bodies or credentials. `plan` needs only PostgreSQL plus the local volume;
`execute` and `verify` require configured MinIO credentials and the exact target bucket.

## Data Model

No schema migration is needed. Existing `Attachment.object_key` and
`DocumentGraphWorkspace.storage_object_key` columns already store scheme-qualified references.
Execution updates a matched pair transactionally. `AuditEvent` records the attachment entity,
action `attachment.object_migrated`, content SHA-256, a SHA-256 of the old key, byte count, workspace
presence and target bucket; it never records the raw source/target key.

## UI / Platform Impact

No public API or UI changes. The command runs inside an API image that has the local object volume,
database connection and managed MinIO secrets mounted. Operators keep the application write backend
unchanged until their rollout step; routed reads continue to support both key forms.

## Observability

Stdout contains only one bounded aggregate JSON result. Audit rows contain hashes/counts and actor
`operator-cli`. Expected validation/storage failures use safe error codes. Provider credentials,
endpoints, object keys, filenames, document bytes and exception text are excluded.

## Alternatives Considered

1. Move then delete each local object. Rejected because rollback and proof would depend immediately
   on remote availability and a partial run could destroy the only copy.
2. Update database references before reading the remote object back. Rejected because an accepted
   upload response is weaker than independent checksum verification.
3. Migrate every row in one transaction. Rejected because it would hold a database transaction over
   the whole external transfer and make large runs non-resumable.
4. Fall back from a remote reference to a same-named local object. Rejected because it hides remote
   outages and makes storage authority ambiguous.

