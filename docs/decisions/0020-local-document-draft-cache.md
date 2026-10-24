# 0020 Local Document Draft Cache

Date: 2026-07-30

## Status

Accepted; the explicit-discard clearing path is superseded by decision 0041.

## Context

Document workspace accepts editable source files but does not let a researcher
author one in place. The owner requires typed content to survive F5. Unsaved
document text may contain sensitive business material, so browser retention
needs an explicit ownership and deletion boundary.

## Decision

Cache one versioned, bounded unsaved authoring draft per authenticated user and
browser origin in `localStorage`. The cache stores title, selected editable
source format, content and update time.

Draft content remains local and is never logged or sent to the server before an
explicit Create action. Create converts the draft into a browser `File` and
uses the existing governed document upload pipeline. Decision 0041 removes the
manual Discard action; the cache now clears only after a successful server
response and remains available on errors.

The authoring cache is limited to two million characters. Uploaded binary
documents are never copied into this cache. Preview remains non-executable.

## Alternatives Considered

1. Store one global browser draft. Rejected because users sharing a browser
   could see each other's content.
2. Use `sessionStorage`. Rejected because browser/tab closure would lose work
   despite the local-first expectation.
3. Add server autosave. Deferred because it requires canonical retention,
   authorization, concurrency and likely schema changes.
4. Cache without a bound. Rejected because browser quota and page performance
   would become unpredictable.

## Consequences

Positive:

- F5 and browser restart do not lose the current user's draft.
- The existing upload, provenance, AI and review pipeline remains authoritative.
- Failed creation never discards unsaved work.

Tradeoffs:

- Browser localStorage is not encrypted and belongs to the local browser
  profile.
- Drafts do not synchronize between browsers or devices.
- Abandoned drafts remain in the identity-scoped browser profile until they are
  overwritten, browser site data is cleared, or creation succeeds.

## Follow-Up

- Add server-side collaborative drafts only through a separately authorized
  data-model and concurrency story.
