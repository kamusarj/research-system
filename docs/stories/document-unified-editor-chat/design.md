# Design

## Domain Model

An editable source import is a bounded UTF-8 browser file mapped to the existing
`DocumentAuthorDraft`. A `DocumentBrainstormRequest` contains current source, one user message,
optional selection offsets and a bounded recent conversation. Its response contains assistant text
and provider/model provenance. It is advisory and has no canonical persistence or mutation power.

## Application Flow

1. Selecting an editable UTF-8 file validates extension, byte size and encoding in the browser.
2. The file populates title, format and source in the existing identity-scoped local draft cache.
3. An explicit brainstorm Send posts current source, offsets and bounded history to the API.
4. The server validates the range, selects a relevant bounded source window, applies existing cloud
   redaction and calls the configured OpenAI/DeepSeek graph-chat provider with no tools.
5. The UI renders the Markdown response. Replace, Insert or Append update only the local editor and
   its cache; they never create a server version by themselves.
6. Create document or Save new version continues through the existing governed workflows.
7. Uploaded LaTeX/reStructuredText/AsciiDoc/HTML join Markdown/TXT in the immutable source editor.

## Interface Contract

- Add `POST /api/v1/documents/brainstorm`.
- Request: current source (maximum two million characters), one bounded message, at most ten recent
  user/assistant messages, optional valid selection offsets, and optional OpenAI/DeepSeek provider.
- Response: assistant content, provider name, model name and whether source context was truncated.
- The route is a researcher mutation under the existing `/documents` role/CSRF/rate boundary.

## Data Model

No migration. Draft source remains in the existing per-user browser cache. Brainstorm messages are
component state for pre-create documents and are not stored in PostgreSQL. Existing uploaded source
versions, RAG rows, research content and audit records remain authoritative.

## UI / Platform Impact

`Document content` and the contextual chat form a responsive workbench: two columns on wide desktop
and one column on Windows laptop/tablet/mobile widths. The standalone upload card is narrowed to
PDF/DOCX; editable source import lives inside the authoring card. Uploaded source detail uses the
same brainstorm component alongside its editor.

## Observability

Provider timing/token observations use the existing graph-chat operation boundary. Logs and audit
payloads exclude document source, selection, user message and response bodies. The API call is
stateless and records no chat row or document change.

## Alternatives Considered

1. Auto-upload every selected source file: rejected because it removes the requested chance to edit
   `Document content` before creation.
2. Auto-apply AI responses: rejected because brainstorming is not consent to overwrite source.
3. Convert DOCX/PDF into editable plain text in place: rejected because saving would silently lose
   layout, embedded media and byte fidelity.
4. Reuse graph chat with a hidden canonical document: rejected because an unsaved local draft has no
   authorized workspace ID and should not create server records merely to brainstorm.
