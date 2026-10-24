# 0036 Document Brainstorm Concurrency and LaTeX Apply Guard

Date: 2026-08-07

## Status

Accepted and implemented locally; strengthens DEC-039, DEC-045 and DEC-046 at the browser boundary.

## Context

Owner asked to hunt hidden Document Brainstorm bugs while keeping manual edit and AI chat edit. Focused
tests were green, but edge cases allowed concurrent apply during pending review, silent chat-edit
outcomes, stale selection ranges, and advisory Apply that could destroy standalone LaTeX.

## Decision

1. Normalize selection against current source before instant edit, chat edit and replace-selection.
2. Instant-edit `run` returns success; chat routing reports `ready`, `selection_required`, `failed`
   or `busy`.
3. Disable brainstorm send while an instant edit is in flight; disable Apply while a reviewed patch
   is pending.
4. Emit local-only chat status for ready/failed edit routing; exclude it from provider history and
   Apply affordances.
5. Refuse brainstorm Apply when the current source is a standalone LaTeX document and the result
   would not remain one.

## Consequences

- Users get explicit chat feedback for edit commands without polluting model context.
- Concurrent mutation races that stale Accept/Reject are blocked.
- Advisory Append/Replace cannot silently break complete LaTeX sources; structural edits stay on the
  reviewed instant-edit path.
