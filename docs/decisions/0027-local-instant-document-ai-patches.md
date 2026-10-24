# 0027 Local Instant Document AI Patches

Date: 2026-08-02

## Status

Accepted; automatic low/medium-risk application superseded by decision 0029.

## Context

Decision 0026 separated advisory brainstorm output from explicit local mutation. The owner now
requests AI selection actions to rewrite the text directly. Free-form chat output and canonical
source offsets are unsafe for this because unsaved browser drafts can diverge while a provider call
is in flight.

## Decision

Add a stateless typed edit-patch endpoint based on the complete current browser source. Each request
contains an opaque local revision and exact target range. Each response echoes those anchors and
adds the original-range SHA-256, replacement, deterministic risk/warnings and provider provenance.

This decision originally allowed low/medium-risk prose patches to replace the exact local range
immediately when revision, range and original text still matched. Decision 0029 now requires every
changed patch to be reviewed before local application. Neither path saves canonical data:
Create/Save remains explicit and is the only operation that creates a source version and triggers
processing or RAG refresh.

## Alternatives Considered

1. Auto-apply free-form brainstorm responses: rejected because commentary is not a valid patch.
2. Accept the existing canonical proposal automatically: rejected because it can ignore unsaved
   local changes and would silently persist provider output.
3. Auto-save the local patch: rejected because instant assistance is not publication consent.
4. Let the provider classify its own risk: rejected because enforcement must be deterministic in
   application code.

## Consequences

Positive:

- Common prose cleanup feels immediate and remains F5-safe through the existing local cache.
- Late or stale provider responses cannot overwrite newer user text.
- Existing immutable version, RAG and graph governance remains authoritative.

Tradeoffs:

- High-risk edits need one Apply click after diff review.
- Undo is local to the latest AI patch; persistent rollback remains source version history.
- Whole-document multi-patch and rich PDF/DOCX editing remain separate work.

## Follow-Up

- Consider atomic multi-patch whole-document consistency edits after single-range behavior is proven.
