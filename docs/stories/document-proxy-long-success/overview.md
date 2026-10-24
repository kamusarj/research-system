# Overview

## Current Behavior

The document instant-edit API completed a real DeepSeek request successfully in 131.115 seconds,
but Next.js aborted its upstream socket at the configured 125-second proxy timeout. The browser
therefore displayed a retryable connection error even though the API logged HTTP 200.

## Target Behavior

Use a bounded, deployment-visible 180-second same-origin proxy timeout. It covers the observed long
success with meaningful transport margin while retaining typed errors and explicit, cost-aware Retry.

## Affected Users

- Owners and researchers running whole-document AI edits.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-ai-edit-reliability/`
- `docs/decisions/0028-document-ai-proxy-budget-and-simple-authoring.md`

## Non-Goals

- Automatic retries, background jobs or unlimited proxy connections.
- Changing provider, API, persistence or review contracts.
