# Design

## Domain Model

The existing revision-bound `DocumentInstantEditPatch` remains the server response. Every changed
patch has `auto_apply_allowed=false` and is held as a browser-only `PendingDocumentInstantEdit`
until the user accepts or rejects it. Risk and warnings remain useful review context but no longer
select a mutation path.

## Application Flow

1. The browser snapshots the exact non-empty selection, source revision and range.
2. The provider receives bounded/redacted context plus an explicit instruction hierarchy: perform
   the requested transformation on the complete selection, preserve protected material unless the
   request specifically transforms it, and return replacement text only in the structured field.
3. The API returns a revision-bound patch or `AI_EDIT_NO_CHANGE` only when replacement equals the
   selected source.
4. The browser verifies that the source revision/range is still current before displaying a review.
5. The review displays complete old/new text. Accept rechecks the binding and edits only the local
   cached draft; Reject discards the patch without changing source.
6. Explicit Create/Save remains the only durable mutation.

## Interface Contract

- Keep `POST /api/v1/documents/edit-in-place` request and response shapes compatible.
- Successful changed responses always set `auto_apply_allowed=false`.
- `AI_EDIT_NO_CHANGE` remains the typed identical-output response.
- Accept/Reject are browser-local actions and create no API request or durable record.

## Data Model

No migration and no new durable data. Pending and accepted edits remain browser draft state until
the existing explicit Create/Save workflow.

## UI / Platform Impact

- Every changed response opens the existing diff review surface.
- Original and replacement panes use removal/addition semantics and remain fully readable.
- Buttons use explicit Accept and Reject labels in English and Vietnamese.
- The review stacks on narrow viewports and does not introduce horizontal overflow.

## Observability

Existing provider/model, duration, action and size metadata remain available. Source, selection,
instruction, replacement and raw provider response remain excluded from logs and audit records.

## Alternatives Considered

1. Keep auto-apply for low-risk prose: rejected by the owner because every actual change must be
   visible before mutation.
2. Persist proposals server-side: rejected because this is an unsaved local-draft workflow and no
   new durable content copy is needed.
3. Infer compliance from the explanation: rejected because the replacement text itself is the only
   content that can be accepted.
