# Exec Plan

## Goal

Make every changed document AI rewrite reviewable as an original/replacement diff with explicit
Accept or Reject, while requiring the provider to perform the user's requested transformation.

## Scope

In scope:

- Instruction-priority prompt rules for built-in and custom rewrite actions.
- Review-before-apply behavior for every changed AI patch.
- Original/replacement comparison and explicit Accept/Reject controls.
- Exact no-change reporting only when normalized provider output equals the selected text.
- Shared behavior in pre-create and uploaded editable-source editors.
- Backend/frontend/component/E2E/responsive proof.

Out of scope:

- Automatic Save/version/RAG/graph changes.
- PDF/DOCX rich editing or collaborative merge.
- Provider streaming, background jobs or automatic paid retries.

## Risk Classification

Risk flags:

- External provider behavior.
- Existing document editing behavior.
- User-visible API/client workflow.
- Cross-platform editor interaction.

Hard gates:

- External provider behavior and AI-generated document mutation.

## Work Phases

1. Record the amended human-review boundary.
2. Strengthen the provider instruction contract and make patches review-only.
3. Replace instant-apply feedback with old/new review and Accept/Reject.
4. Update deterministic backend and frontend tests.
5. Run focused/full checks and responsive interaction proof.
6. Update product truth, Harness proof/trace and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- The requested transformation would require automatic canonical Save.
- Redaction, source/range limits, authorization or rate limiting need weakening.
- The API must store document text or provider output.
- Validation requirements need to be reduced.
