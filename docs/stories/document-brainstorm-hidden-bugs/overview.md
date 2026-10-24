# Overview

## Current Behavior

Document Brainstorm and instant edit coexist, but several edge cases left the draft unsafe or the
chat silent: concurrent chat apply while a reviewed patch was pending, stale selection ranges after
manual edits, edit-command success/failure with no chat feedback, and advisory Append/Replace that
could destroy standalone LaTeX structure.

## Target Behavior

Manual editing and AI chat editing remain available together. Chat edit commands still create a
reviewed Accept/Reject patch. While a patch is busy or pending, brainstorm send/apply is locked.
Invalid selections are dropped. Chat reports ready/failed/busy outcomes without sending local status
text to the provider. Advisory apply refuses mutations that would break a standalone LaTeX document.

## Affected Users

- Owners and researchers editing Markdown/TXT/LaTeX source in Document workspace.

## Affected Product Docs

- `docs/decisions/0026-stateless-document-editor-brainstorm.md`
- `docs/decisions/0032-route-document-chat-edit-intent.md`
- `docs/decisions/0033-preserve-whole-source-latex-edits.md`

## Non-Goals

- No automatic Accept.
- No PDF/DOCX rich editing.
- No durable brainstorm chat history.
