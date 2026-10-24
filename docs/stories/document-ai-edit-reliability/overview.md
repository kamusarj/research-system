# Reliable and Simple Document AI Editing

## Current Behavior

A provider response that exceeds Next.js's default 30-second rewrite-proxy timeout becomes a raw
`Request failed (500)` in the editor even when the API later succeeds. No retry action is offered.
The pre-create page permanently repeats the draft in a second large source/preview card and presents
secondary policy/explanation content at the same visual weight as the editor.

## Target Behavior

The same-origin proxy permits the full configured AI request budget. Provider and malformed-response
failures remain typed, localized and actionable; only transient errors show a user-triggered Retry.
The authoring surface prioritizes title, format, import, editor, AI and Create. Safe preview modes
remain available but are collapsed until requested. Binary upload and existing documents remain
compact secondary workflows.

## Affected Users

- Owners and researchers authoring or editing documents.
- Viewers are unaffected and remain read-only.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-instant-ai-edit/`
- `docs/decisions/0027-local-instant-document-ai-patches.md`

## Non-Goals

- No background job or streaming provider architecture.
- No automatic paid-provider retry.
- No removal of Raw/Preview/Side-by-side modes.
- No PDF/DOCX rich editing.
- No persistence, RAG, graph or authorization change.
