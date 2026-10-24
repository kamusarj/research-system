# Structured Document Graph Provider Reliability

## Current Behavior

Document processing validates paper-fit and document-graph provider responses independently. In the
live acceptance walkthrough, Mistral returned a valid paper-fit evaluation but its document-graph
response failed strict validation with `AI_RESPONSE_INVALID`; the workspace required a manual retry
with DeepSeek.

## Target Behavior

An invalid structured document-graph response gets one bounded recovery request to the same selected
provider with explicit validation feedback. The recovered response must pass the unchanged Pydantic
schema before persistence. If recovery fails, processing retains the existing typed error and manual
retry path.

## Affected Users

- Product owners uploading source documents for graph review.
- Local operators diagnosing provider reliability.

## Affected Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Graph Intelligence v2 Operations Runbook.md`
- `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`

## Non-Goals

- No automatic switch to another provider.
- No mock, partial, or unvalidated graph persistence.
- No public API, database schema, or frontend workflow change.
- No change to durable job retry limits or manual provider selection.
