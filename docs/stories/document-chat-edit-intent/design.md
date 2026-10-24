# Design

## Domain Model

An edit imperative is a chat message beginning with an optional polite prefix and a supported
Vietnamese/English mutation verb. It is routed to the existing `DocumentInstantEditPatch` model;
no new patch type is introduced.

## Application Flow

1. The user explicitly sends a contextual chat message.
2. Deterministic client routing distinguishes edit imperatives from advisory questions.
3. An edit imperative targets the native selection, or the whole source when no selection exists
   and it remains within 20,000 characters.
4. The parent editor calls the existing custom instant-edit hook with the exact instruction.
5. The chat does not call advisory Brainstorm and does not append explanatory AI prose.
6. Existing revision/range checks render complete Original/Proposed content; only Accept updates the
   local cached draft and Reject preserves it.

## Interface Contract

No API shape changes. `POST /api/v1/documents/edit-in-place` is reused with `action=custom`; the
existing brainstorm endpoint remains for non-edit messages.

## Data Model

No schema, migration or retention change.

## UI / Platform Impact

Both pre-create authoring and uploaded editable documents pass the same edit callback into the
shared chat. Oversized whole-source edits ask the user to select a bounded target. Existing diff
and Accept/Reject components remain authoritative.

## Observability

Provider telemetry records `document-instant-edit`, not `document-editor-brainstorm`, for routed
commands. Prompt/source bodies remain excluded from logs.

## Alternatives Considered

1. Ask the provider to classify intent before editing: rejected because it doubles latency/cost and
   introduces a second failure before the actual patch.
2. Parse free-form brainstorm prose into a patch: rejected because it is unstructured and unsafe.
3. Keep generic Replace/Insert/Append only: rejected by the owner because it lacks source-bound
   Original/Proposed Accept/Reject review.
