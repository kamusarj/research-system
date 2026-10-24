# 0014 Copy-Verify Object Migration

Date: 2026-07-21

## Status

Accepted

## Context

Plain object keys permanently route to the local document volume and remote keys route to MinIO.
Gate C needs a safe transition path, but merely changing the write backend does not migrate durable
references. Removing the local volume without a checksummed copy/read-back process would risk silent
document loss.

## Decision

Add an operator-only, dry-run-first migration command. Execution requires explicit copy-only
confirmation, validates the complete local inventory before copying, streams each source to the
configured MinIO object name, reads the remote copy back, compares size and SHA-256, rechecks the
local source, then transactionally changes the matched attachment/workspace references and writes
bounded audit evidence. Each object commits independently so reruns converge. The command never
deletes local objects or volumes.

## Alternatives Considered

1. Move/delete during migration: rejected because the local copy is required for rollback and
   independent verification.
2. Trust MinIO upload success without read-back: rejected because it does not prove durable byte
   parity at the application boundary.
3. One global database transaction: rejected because external copy duration and partial failure
   make it unsafe and non-resumable.
4. Silent remote-to-local read fallback: rejected because it hides production storage outages.

## Consequences

Positive:

- Operators can inventory, copy, verify and resume without changing public APIs or schemas.
- Database references never point to an unverified remote object.
- The retained local copy plus aggregate/audit evidence supports a later independent retirement
  decision.

Tradeoffs:

- Large migrations are sequential and intentionally favor bounded memory/integrity over speed.
- A crash after remote copy but before database commit may leave an orphan remote object; a rerun
  deterministically overwrites and verifies it.
- Migrated remote references still require MinIO read availability even when new writes roll back
  to local.

## Follow-Up

- Production operators own MinIO TLS/KMS/replication/backup and database/local-volume snapshots.
- Local volume cleanup remains a separate maintenance action after successful `verify`, backup and
  explicit human authorization; this repository intentionally provides no delete mode.

