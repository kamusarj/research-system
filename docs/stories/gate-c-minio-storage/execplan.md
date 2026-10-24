# Exec Plan

## Goal

Add reversible MinIO/S3-compatible attachment storage without losing access to existing local
objects or exposing storage credentials.

## Scope

In scope:

- MinIO SDK adapter for bounded put/open/delete.
- Scheme-qualified remote keys and local-key compatibility router.
- Typed environment settings for endpoint, TLS, bucket and credentials.
- Unit/contract tests and one isolated live MinIO round trip.
- Deployment/runbook documentation and Harness evidence.

Out of scope:

- Automatic object migration, lifecycle deletion or retention policy.
- Bundled production MinIO server, replication, erasure coding or backup automation.
- Auth/RBAC, secret manager, OCR/browser processing and Discord.

## Risk Classification

Risk flags:

- Data ownership/storage.
- Audit/security.
- External systems.
- Existing behavior.
- Cross-platform deployment.
- Weak integration proof before a live round trip.

Hard gates:

- External storage behavior.
- Sensitive credential handling.
- Existing-object availability.

## Work Phases

1. Lock the opaque-key routing decision.
2. Implement settings, adapter and router.
3. Add deterministic failure/compatibility tests.
4. Update deployment documentation.
5. Run full regression and isolated live MinIO proof.
6. Record story, trace and AI handoff evidence.

## Stop Conditions

Pause for human confirmation if:

- Existing object keys require destructive migration.
- The public upload/download contract must change.
- Production server lifecycle or secret-manager choice becomes required for adapter correctness.
- Validation would require storing a real credential in the repository or logs.
