# 0029 Review Every Document AI Edit

Date: 2026-08-04

## Status

Accepted

## Context

The instant-edit workflow currently applies low/medium-risk output to the local draft before the
user can compare it. The owner requires AI to follow the requested transformation and, whenever
the result changes text, show old and new content with Accept or Reject like an editor diff.

## Decision

Every changed document AI patch remains review-only regardless of risk classification. The browser
shows the complete original/replacement comparison and modifies the local draft only after explicit
Accept; Reject discards it. The provider prompt treats the user's selected action/custom instruction
as a required transformation over the complete selected range. Identical output alone is reported
as no change. Existing revision/range conflict checks, stateless provider boundary, redaction,
authorization, rate limits and explicit Create/Save persistence remain unchanged.

## Alternatives Considered

1. Retain automatic application for low/medium risk and offer Undo afterward. This does not meet
   the requested before-mutation review model.
2. Create durable server-side proposals. This duplicates unsaved document content and is not needed
   for a local draft decision.

## Consequences

Positive:

- Users see exactly what AI proposes before any text changes.
- Accept/Reject is consistent for prose, facts, syntax and custom transformations.
- The provider has a clearer instruction-compliance contract.

Tradeoffs:

- Even simple grammar fixes now require one additional click.
- `auto_apply_allowed` remains in the compatible response shape but is always false.

## Follow-Up

- Verify the review interaction and no-overflow behavior across supported viewports.
