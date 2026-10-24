# Design

## Domain Model

An instant edit is a stateless `DocumentEditPatch`: opaque source revision, exact source range,
SHA-256 hash of the original range, replacement text, explanation, risk classification, warnings
and provider provenance. The server computes risk from action, instruction and protected syntax.
The browser owns the unsaved draft and an in-memory one-patch undo record.

## Application Flow

1. The browser resolves an exact non-empty selection and snapshots source, revision and range.
2. `POST /api/v1/documents/edit-in-place` validates source/range/action and chooses bounded adjacent
   context before redaction and provider invocation.
3. The provider returns structured replacement text and explanation only; it cannot select the
   range, mutate storage or call tools.
4. The server returns the patch with original hash and deterministic risk/warnings.
5. The browser compares current revision, range and original text with the snapshot.
6. Low/medium-risk patches replace the range immediately in local draft/cache. High-risk patches
   show a diff and require Apply. All applied patches expose Undo and View diff.
7. Create/Save later persists the complete draft through existing governed version/RAG processing.

## Interface Contract

- Add `POST /api/v1/documents/edit-in-place` under the existing document researcher boundary.
- Request: source ≤2,000,000 characters, source revision ≤128 characters, exact range ≤20,000
  characters, action, optional custom instruction/source format and OpenAI/DeepSeek provider.
- Response: echoed revision/range, original SHA-256, replacement ≤40,000 characters, explanation,
  risk (`low|medium|high`), `auto_apply_allowed`, bounded warnings and provider/model provenance.
- Typed errors cover invalid range, empty selection, no-change and provider failures.

## Data Model

No migration. Instant-edit calls do not create document, chat, proposal, version or audit rows.
Applied source remains in existing per-user browser draft cache until explicit Create/Save.

## UI / Platform Impact

Both direct authoring and uploaded-source editors use the same instant-edit hook/component. Native
selection actions show progress, then select the replacement range. A compact change bar exposes
Undo/View diff and risk warnings without obscuring the editor. The layout must remain usable at
1920, Windows 1366, tablet and mobile widths.

## Observability

Operational observations may include provider/model, duration, action, source/selection character
counts, risk and success/error code. Source, selection, instruction, replacement and response body
must not be logged or audited.

## Alternatives Considered

1. Apply free-form brainstorm Markdown: rejected because explanations can be inserted as source.
2. Reuse durable AI proposals for every edit: rejected because an unsaved local draft can diverge
   from canonical source and instant local assistance should not create hidden database rows.
3. Auto-save after provider response: rejected because provider output is not canonical approval.
4. Apply fact/citation/code changes without review: rejected because semantic or syntax corruption
   has materially higher impact than prose cleanup.
