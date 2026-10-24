# 0026 Stateless Document-Editor Brainstorm

Date: 2026-08-02

## Status

Accepted

## Context

Authors need AI brainstorming against source that may still exist only in the browser, while
uploaded source editing and document-scoped graph chat currently require a canonical workspace.
Creating a hidden document or auto-saving merely to ask a question would change retention and data
ownership. Applying an answer automatically would violate the accepted human-review boundary.

## Decision

Add a stateless document-editor brainstorm call. Every explicit Send includes bounded current
source, valid optional selection offsets and recent local conversation. The server selects a
relevant context window, applies existing cloud redaction and invokes the configured OpenAI or
DeepSeek graph-chat provider with no tools and provider-side storage disabled where supported.

The reply is advisory. Replace selection, Insert at cursor and Append are explicit browser actions
that update the local editor/cache only. Create or Save remains a second explicit governed action.
No pre-create chat rows, source versions, graph changes or audit bodies are persisted.

Editable UTF-8 imports load locally into the existing author draft before creation. Post-upload
immutable editing expands to all accepted UTF-8 source formats. PDF/DOCX remain binary references
until a separate format-faithful editing design exists.

## Alternatives Considered

1. Hidden temporary document/chat rows: rejected because asking a question should not silently
   create durable source and chat records.
2. Browser-direct provider calls: rejected because credentials and policy must remain server-side.
3. Automatic response application: rejected because AI output is not user approval.
4. Plain-text overwrite of DOCX/PDF: rejected because it destroys document fidelity.

## Consequences

Positive:

- Users can brainstorm before upload and beside uploaded editable source.
- Provider transmission and document mutation are separate explicit actions.
- Existing cache, immutable version, RAG and graph governance stay authoritative.

Tradeoffs:

- Pre-create brainstorm history is not durable across refresh unless later added to the local cache.
- Very long source is relevance-windowed and the UI must disclose truncated provider context.
- DOCX/PDF still require a future rich-format editing story.

## Follow-Up

- Design byte-faithful DOCX/PDF editing only as a separate high-risk story.
