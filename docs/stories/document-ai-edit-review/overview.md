# Reviewed Document AI Edits

## Current Behavior

Low/medium-risk AI rewrites replace the selected range in the browser draft immediately and only
show a diff after the mutation. High-risk edits already show an original/replacement comparison.
The provider prompt asks it to preserve content, but does not state strongly enough that an explicit
user transformation is mandatory and applies to the complete selected range.

## Target Behavior

Every provider result that differs from the selected text remains a pending browser-only proposal.
The editor shows the complete original and replacement in a diff-style review and changes the local
draft only after Accept. Reject discards the result without changing source. The provider must apply
the explicit user instruction to the entire selection, including format conversions such as LaTeX;
the UI reports no change only when the returned replacement is actually identical.

## Affected Users

- Owners and researchers editing supported UTF-8 source documents.
- Viewers remain read-only.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-instant-ai-edit/`
- `docs/stories/document-ai-edit-reliability/`
- `docs/decisions/0027-local-instant-document-ai-patches.md`

## Non-Goals

- No automatic canonical Save, version creation, RAG rebuild or graph publication.
- No database migration or durable proposal record.
- No lossy PDF/DOCX editing.
- No weakening of conflict, redaction, authorization, timeout or rate-limit controls.
