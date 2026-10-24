# Overview

## Current Behavior

Document uploads can write to local storage or managed MinIO. Plain object keys permanently route
to the local volume and `minio://<bucket>/...` keys route to MinIO. Existing local objects remain
readable after the write backend changes, but there is no inventory, checksummed copy command or
proof that would let an operator migrate references safely. Removing the legacy volume would
therefore be unverified data loss.

## Target Behavior

Provide an operator-only CLI with `plan`, explicitly confirmed `execute`, and `verify` modes.
Planning inventories legacy attachment references and validates local size/SHA-256 without changing
state. Execution copies eligible local objects to the configured MinIO bucket, reads them back,
requires byte count and SHA-256 parity, then transactionally changes the attachment/workspace
references and records bounded audit metadata. Verification proves the remote copy and retained
local source still match. No mode deletes a local object or volume.

The command is resumable: each object/reference pair commits independently only after verification;
a repeat run skips already migrated references and converges after an interrupted copy.

## Affected Users

- Deployment operators planning or executing the local-to-MinIO transition.
- Researchers relying on uploaded documents remaining downloadable and processable.
- Owners reviewing migration audit evidence and authorizing any later volume retirement.

## Affected Product Docs

- `README.md`
- `Docs/Research System Completion Plan.md`
- `Docs/Graph Intelligence v2 Operations Runbook.md`
- `docs/decisions/0008-routed-object-storage.md`

## Non-Goals

- Deleting local objects, unmounting the volume or automating retention.
- Migrating metadata-only attachment references whose local bytes are missing or inconsistent.
- Provisioning, upgrading, backing up or encrypting a production MinIO cluster.
- Adding a public HTTP migration endpoint or browser UI.
- Falling back from an unavailable remote key to a same-named local object.

