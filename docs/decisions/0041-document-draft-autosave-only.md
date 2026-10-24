# 0041 Document Draft Autosave Without Manual Discard

Date: 2026-08-11

## Status

Accepted

## Context

The authoring cache already writes every title, format and content change to a
bounded, identity-scoped browser draft and restores it after refresh or browser
restart. The owner identified the manual `Discard local draft` action as an
unnecessary data-loss path during active work and explicitly requested its
removal.

## Decision

Preserve immediate synchronous `localStorage` writes, the existing versioned key
and value shape, per-user scoping, two-million-character bound, failure retention
and refresh/restart restoration. Remove the manual discard control and handler.

A successful governed Create remains the only normal product event that clears
the completed pre-create cache. Draft content remains local and is not sent or
logged before Create. This decision supersedes only the explicit-discard clearing
path in decision 0020.

## Alternatives Considered

1. Keep the destructive action with a confirmation dialog. Rejected because it
   still preserves an unnecessary whole-draft loss path.
2. Move autosave to the server. Rejected because the requested crash protection
   is already provided locally and server drafts require a separate retention,
   authorization and concurrency design.
3. Debounce local writes. Rejected because it introduces a loss window before a
   crash or accidental close.

## Consequences

Positive:

- Accidental use of a product-level discard action can no longer erase the draft.
- Existing drafts survive deployment because the storage schema is unchanged.
- Browser crash/restart recovery remains synchronous and network-independent.

Tradeoffs:

- Abandoned drafts remain in that user's browser profile until overwritten,
  browser site data is cleared, or the document is successfully created.
- `localStorage` remains unencrypted and does not synchronize across devices.

## Follow-Up

- Treat collaborative or cross-device server drafts as a separate high-risk
  data-model and concurrency story if requested later.

