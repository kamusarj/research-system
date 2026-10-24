# Exec Plan

## Goal

Let AI rewrite selected document source in place immediately while protecting newer user edits and
keeping canonical persistence explicit.

## Scope

In scope:

- Stateless structured edit-patch API.
- Revision/range/original-text conflict protection.
- Immediate local apply for low/medium risk plus Undo/View diff.
- Review-only handling for protected facts, citations, URLs, code and formulas.
- Shared behavior in pre-create and uploaded editable-source editors.
- Backend/frontend/E2E/responsive/runtime proof.

Out of scope:

- Automatic Save/version/RAG/graph changes.
- Whole-document autonomous multi-patch rewriting.
- PDF/DOCX rich editing and collaborative merge.

## Risk Classification

Risk flags:

- External provider behavior.
- Additive public API contract.
- Existing document editing and cache behavior.
- Audit/privacy boundary.
- Cross-platform selection interaction.

Hard gates:

- Provider-bound document text and automatic local mutation.

## Work Phases

1. Record the amended mutation boundary and typed patch contract.
2. Implement schemas, service, route and deterministic provider tests.
3. Add shared client contract and conflict-safe local patch application.
4. Replace selection actions in both editors and add Undo/View diff/review-only behavior.
5. Run focused/full backend, frontend, E2E, responsive and runtime proof.
6. Update product truth, Harness proof/trace and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- Canonical auto-save becomes necessary.
- Protected fact/citation/code edits cannot remain review-only.
- Redaction, source/range limits, role or CSRF checks need weakening.
- A schema migration or destructive data change appears.
