# Exec Plan

## Goal

Deliver a non-destructive, checksummed and resumable operator command plus operational proof for
migrating legacy local document objects to managed MinIO without weakening the routed-storage
contract.

## Scope

In scope:

- Aggregate local-object inventory and integrity validation.
- Explicitly confirmed copy-only execution with remote read-back verification.
- Transactional attachment/workspace reference updates and bounded audit evidence.
- Repeat/interruption convergence and dry-run/negative tests.
- Read-only inventory on the current main runtime and disposable real-MinIO proof.

Out of scope:

- Running the migration against the main runtime without separate operator authorization and
  production MinIO configuration.
- Local-object/volume deletion or automated cleanup.
- MinIO provisioning, TLS, KMS, replication, lifecycle and backup implementation.
- Intake receipt schema or Discord adapter work.

## Risk Classification

Risk flags:

- Data migration and persistent reference changes.
- External MinIO storage.
- Audit/security and sensitive object metadata.
- Existing upload/download/worker behavior.
- Weak proof for interruption and real-service parity.

Hard gates:

- Data loss/migration.
- External provider behavior.
- Audit/security.

## Work Phases

1. Inventory current attachment/workspace/reference behavior and accepted storage decision.
2. Lock the copy-only/checksum/transaction/audit design.
3. Implement the service and explicit operator CLI.
4. Add deterministic plan/execute/verify/failure/resume tests.
5. Run full regression, main read-only plan and disposable real-MinIO proof.
6. Update operations docs, Harness proof and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- Any step would delete or overwrite the local source volume.
- Existing rows cannot be reconciled without inventing bytes, hashes or references.
- The command would need to weaken checksum/read-back requirements.
- Main-runtime execution rather than read-only planning is requested without a managed target,
  backup and explicit maintenance approval.

