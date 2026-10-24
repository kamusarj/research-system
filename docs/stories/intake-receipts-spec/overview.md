# Overview

## Current Behavior

`LinkSubmission` is both source occurrence and URL processing job. Its normalized URL is unique, so
a repeated URL returns the original row and loses the later source occurrence's provenance. One
external message cannot durably own multiple URL/document items.

## Target Behavior

Accept `Docs/Intake Occurrence and Receipt Specification.md` as the source-neutral contract. A
receipt represents one external occurrence, receipt items represent its URLs/documents, and existing
submission/workspace rows remain processing aggregates. The design defines idempotency, safe
provenance, public API, attachment durability, additive migration, authorization, and proof gates
before any Discord implementation.

## Affected Users

- Researchers submitting URLs/documents manually.
- Owners reviewing provenance and publication decisions.
- Future scoped service accounts and thin external adapters.
- Operators migrating and observing intake state.

## Affected Product Docs

- `Docs/Intake Occurrence and Receipt Specification.md`
- `Docs/Research System Completion Plan.md`
- `Docs/Research System Architecture Design.md`
- `Docs/Source Processing Pipeline.md`

## Non-Goals

- Do not implement Discord in this story.
- Do not implement a migration, endpoint, service account, Discord bot, webhook, or live platform
  integration in this story.
- Do not change current runtime data or execute external deployment operations.
- Do not relax Graph v2 acceptance or Gate C entry criteria.
