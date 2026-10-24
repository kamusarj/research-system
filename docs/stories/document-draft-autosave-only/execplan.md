# Exec Plan

## Goal

Prevent accidental loss of an in-progress Document Workspace draft by removing
manual discard while preserving immediate local autosave and restart recovery.

## Scope

In scope:

- Remove the authoring discard handler and button.
- Remove obsolete EN/VI discard copy.
- Keep synchronous per-change cache writes and restore behavior.
- Keep failure retention and success-only cache clearing.
- Update component, browser and product-contract proof.

Out of scope:

- Server-side, collaborative or cross-device drafts.
- Uploaded workspace editor cache behavior.
- API, database, auth, AI, RAG, graph or publication changes.

## Risk Classification

Risk flags:

- Audit/security: unsaved business text remains retained in browser storage.
- Existing behavior: an implemented and tested destructive action is removed.
- Cross-platform: browser persistence is user-visible on desktop/tablet/mobile.

Hard gates:

- Local retention of potentially sensitive source text.

## Work Phases

1. Confirm current cache and clear boundaries.
2. Record the success-only clearing decision.
3. Remove the discard UI/handler and obsolete translations.
4. Update unit and browser regression coverage.
5. Run focused tests, lint, typecheck and production build.
6. Record Harness and AI handoff evidence.

## Stop Conditions

Pause for human confirmation if:

- The change requires server persistence or a schema migration.
- Identity scoping or the two-million-character bound would be weakened.
- Successful creation can no longer clear its completed pre-create draft.
- Existing authorization or publication boundaries would change.

