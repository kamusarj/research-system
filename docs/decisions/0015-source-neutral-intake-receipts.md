# 0015 Source-Neutral Intake Receipts

Date: 2026-07-21

## Status

Accepted

## Context

The current unique normalized URL on `LinkSubmission` prevents duplicate work but conflates a
processing job with the external occurrence that submitted it. Repeated URLs lose later source
provenance, and one Discord message with multiple URLs or a PDF cannot be represented safely.

## Decision

Introduce an additive two-level model in a later implementation story: `IntakeReceipt` represents
one source-neutral external occurrence, and `IntakeReceiptItem` represents each URL or document in
that occurrence. Existing `LinkSubmission` and `DocumentGraphWorkspace` remain canonical processing
aggregates. Receipt/item hashes make identical deliveries idempotent, while different occurrences
of the same URL create distinct provenance linked to the same processing job.

Receipt delivery is append-only. Document bytes must be validated, stored and hash-verified before
asynchronous acknowledgement. Source metadata and audit are allowlisted and exclude payload bodies,
user profiles, credentials and raw sensitive values. Existing intake behavior migrates additively
and keeps legacy provenance columns through rollback verification.

## Alternatives Considered

1. Overwrite provenance on the unique URL job: rejected because it destroys occurrence history.
2. Create a complete URL job per occurrence: rejected because it duplicates fetch/AI processing.
3. Store occurrences as JSON on the URL job: rejected because it lacks concurrency guarantees,
   referential integrity and a clean multi-item contract.
4. Keep receipts only in Discord: rejected because it creates an adapter-owned source of truth.

## Consequences

Positive:

- Same message + normalized URL retries converge; different messages preserve independent
  provenance without duplicate URL processing.
- Manual/API/Discord and later adapters share one contract.
- Multi-URL messages and persisted document attachments have explicit ownership and status.
- Discord remains a thin adapter and PostgreSQL remains canonical.

Tradeoffs:

- Two additive tables, a backfill, dual-write transition and scoped service-account authorization
  are required before Gate D.
- Receipt aggregate status is a projection over linked workflows and must not drift into another
  publication state machine.
- Object storage and PostgreSQL cannot form one transaction, so cleanup/reconciliation proof is
  required for document items.

## Follow-Up

- Implement the additive schema, service/API, backfill, auth scopes and proof in a separate
  high-risk story.
- Do not implement Discord until the entry criteria in the accepted specification pass.

