# Overview

## Current Behavior

The accepted receipt contract exists only in documentation. Runtime still returns one unique-URL
`LinkSubmission`, overwrites no provenance but cannot retain later occurrences, cannot group multiple
items, and has no scoped service-account authentication for external intake clients.

## Target Behavior

Implement the additive receipt/item schema and backfill, source-neutral URL/document APIs,
compatibility dual-write, namespace-scoped revocable service accounts, safe audit projections and
all proof required by `Docs/Intake Occurrence and Receipt Specification.md`.

## Affected Users

- Manual researchers using the current ingestion UI/API.
- Owners provisioning/revoking intake service accounts.
- Future external adapters that submit and poll only their namespace.
- Operators applying and validating the additive migration.

## Affected Product Docs

- `Docs/Intake Occurrence and Receipt Specification.md`
- `Docs/Research System Completion Plan.md`
- `Docs/Source Processing Pipeline.md`
- `README.md`

## Non-Goals

- Do not implement Discord, callbacks/webhooks, platform credentials, guild/channel policy, or bot
  reactions/replies.
- Do not delete legacy provenance columns, receipts, receipt items, jobs, documents, or objects.
- Do not execute production object migration or claim product-owner Graph v2 acceptance.

