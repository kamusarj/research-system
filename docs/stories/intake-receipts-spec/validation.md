# Validation

## Proof Strategy

This is a docs/decision story. Proof requires the specification to cover the observed current gap,
domain/data/API/idempotency/attachment/auth/audit/migration/concurrency contracts, validation ladder,
and explicit Discord gate without changing runtime code or data.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Static required-section and invariant checks; balanced Markdown fences. |
| Integration | Cross-document consistency across Completion Plan, Architecture and Source Pipeline. |
| E2E | Static end-to-end contract scenarios for replay, repeated occurrence, multi-item receipt and durable attachment; no runtime implementation claim. |
| Platform | Explicit Discord non-implementation and Gate D entry criteria. |
| Performance | Future implementation requires bounded items and concurrent replay proof. |
| Logs/Audit | Spec explicitly excludes payloads, secrets and raw source details. |

## Fixtures

- Same message + same normalized URL replay.
- Different message + same normalized URL repeated occurrence.
- One message with multiple URLs.
- One message with URL plus PDF attachment.
- Same external attachment ref with same and different content hashes.
- Concurrent identical deliveries.
- Legacy rows with and without `source_ref`.

## Commands

```text
bash scripts/verify_intake_receipt_spec.sh
scripts/bin/harness-cli story verify US-INTAKE-RECEIPTS-SPEC
git diff --check
```

## Acceptance Evidence

- `bash scripts/verify_intake_receipt_spec.sh` returns `INTAKE_RECEIPT_SPEC_OK`.
- Required domain/API/idempotency/document/auth/audit/concurrency/migration/Gate D sections and
  replay/repeated-occurrence/multi-item scenarios are present.
- Completion Plan, Architecture and Source Pipeline link the accepted target while clearly marking
  schema/API/Discord implementation as pending.
- Markdown fences and scoped `git diff --check` pass.
- Proof is contract/static evidence only and does not claim a migrated runtime or Discord adapter.
