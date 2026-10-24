# 0032 Route Document-Chat Edit Intent to Reviewed Patches

Date: 2026-08-04

## Status

Accepted and implemented locally; amends decision 0026 for direct edit imperatives without
changing advisory brainstorm behavior for questions and ideation.

## Context

Contextual Document Brainstorm originally treated every message as advisory. A direct command such
as `sửa tên thành Bùi Hoàng Linh` therefore returned explanatory prose and generic insertion
controls instead of the existing source-bound Original/Proposed Accept/Reject review the owner
requires for AI changes.

## Decision

Route deterministic Vietnamese and English edit imperatives from contextual document chat into the
existing custom instant-edit pipeline. Target the current selection when present; otherwise target
the complete source only within the established 20,000-character selection bound. Keep questions
and brainstorming prompts on the advisory brainstorm endpoint.

Every routed result remains a revision/range-bound pending patch. The full original and replacement
must be visible, Accept is the only local mutation action, Reject preserves source, and Create/Save
remains the only durable mutation boundary.

## Alternatives Considered

1. Provider-based intent classification: rejected because it adds cost, latency and another failure
   before the actual edit.
2. Convert advisory Markdown replies into patches: rejected because free-form output is not a safe
   or exact source replacement contract.
3. Continue requiring users to discover the separate selection toolbar: rejected because the owner
   explicitly expects direct edit commands in the contextual chat to produce reviewable edits.

## Consequences

- One explicit Send makes at most one provider call: brainstorm or instant edit, never both.
- Supported direct commands produce no explanatory brainstorm response.
- Oversized whole-source edits require a bounded native selection.
- No API, database, retention, RAG, graph, auth or audit boundary changes.
