# Design

## Domain Model

`DocumentGraphWorkspace.research_id` identifies the canonical `ResearchItem.content` produced by
the bounded extraction worker. Document chat may read only this canonical text for the workspace
selected in the chat session.

## Application Flow

1. Validate the document scope as today.
2. Load the linked ResearchItem.
3. Add at most half of the configured total chat-context character budget as `document_text`.
4. Serialize the whole scope context.
5. Apply existing cloud redaction.
6. Apply the existing final `chat_max_context_chars` bound.
7. Send through the existing provider-neutral chat adapter.

## Interface Contract

No public HTTP route changes. The internal provider instructions gain `document_text` and a
`document_text_truncated` boolean for document-scoped sessions.

## Data Model

No migration or retention change. Chat messages stay local; provider requests continue using the
configured adapter and `store: false` where supported.

## UI / Platform Impact

The existing “Brainstorm with document” action becomes capable of Q&A over canonical extracted
text. No UI control or permission changes.

## Observability

Existing provider latency/token observations and chat request provenance remain in use. Document
content is not added to logs, audit payloads or tool-result persistence.

## Alternatives Considered

1. Evidence-only context: safer but insufficient for questions about passages not selected into
   document graph nodes.
2. Full original file: rejected because binary/raw markup is unnecessary and may exceed bounds.
3. Canonical bounded text: selected because it is already parsed, AI-readable and governed by the
   existing redaction/context boundary.
