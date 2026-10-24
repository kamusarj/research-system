# Exec Plan

## Goal

Let users import editable source into `Document content`, edit it before creation, and brainstorm
with AI beside both new and uploaded source without silent mutation.

## Scope

In scope:

- Browser import for Markdown/TXT/LaTeX/reStructuredText/AsciiDoc/HTML into the authoring draft.
- Post-upload immutable editing for those same UTF-8 formats.
- Stateless bounded/redacted document brainstorm endpoint.
- Reusable responsive brainstorm panel with explicit Replace/Insert/Append actions.
- Backend, frontend, E2E, build and runtime proof.

Out of scope:

- Rich DOCX/PDF round-trip editing.
- Collaborative drafts, server autosave or persisted pre-create chat sessions.
- Automatic document mutation, save, RAG rebuild or graph publication.

## Risk Classification

Risk flags:

- External provider behavior.
- Additive public API and user-visible workflow.
- Existing upload, authoring, editing and cache behavior.
- Cross-platform responsive interaction.
- Multiple document/chat domains.

Hard gates:

- Provider-bound potentially sensitive document text.

## Work Phases

1. Record story and stateless provider/data-ownership decision.
2. Add bounded schemas, context selection, provider service and API proof.
3. Add editable-file import and broaden safe source-version formats.
4. Add reusable contextual chat and explicit local apply actions.
5. Run focused/full backend and frontend proof, responsive E2E and runtime smoke.
6. Update product truth, Harness proof/trace and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- DOCX/PDF fidelity would need to be discarded or rewritten.
- Brainstorming would require automatic save/apply or provider-side retention.
- Role, CSRF, redaction or context bounds would need weakening.
- A schema migration or deletion becomes necessary.
