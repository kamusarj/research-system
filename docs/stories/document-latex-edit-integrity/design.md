# Design

## Domain Model

A `standalone LaTeX source` contains an unfenced `\\documentclass`, followed by
`\\begin{document}` and a terminal `\\end{document}`. Before `\\documentclass` and after
`\\end{document}`, only whitespace or comment-only lines are allowed.

Source-format integrity is a patch invariant when the selected range is the complete current source
and that source is already a standalone LaTeX document.

## Application Flow

1. Contextual chat routes the rename imperative to the existing custom instant-edit request.
2. The backend recognizes that the complete selected source is a standalone LaTeX document.
3. The prompt explicitly requires a complete standalone replacement with no fences or commentary.
4. The backend validates the provider payload before returning a patch.
5. The browser repeats the structural check before exposing a pending Accept action.
6. A noncompliant payload becomes the existing typed invalid-response error; Raw remains unchanged.

## Interface Contract

No request or success-response shape changes. `POST /api/v1/documents/edit-in-place` returns the
existing `AI_RESPONSE_INVALID` error when a whole-source LaTeX replacement breaks the source
structure.

## Data Model

No schema, migration, persistence or retention change.

## UI / Platform Impact

The existing localized invalid-response feedback and explicit Retry remain in use. Invalid provider
text never appears as Proposed content and cannot reach Raw through Accept. Valid patches retain the
existing Original/Proposed Accept/Reject workflow.

## Observability

Existing provider outcome telemetry records the typed invalid response without logging source,
instruction or replacement bodies.

## Alternatives Considered

1. Trust prompt wording alone: rejected because the screenshot proves providers can still return
   explanatory prose.
2. Compile every replacement before review: rejected because edits should remain lightweight and
   compilation has a separate bounded endpoint.
3. Validate every LaTeX fragment as standalone: rejected because partial selections are allowed to
   contain plain text or local commands.
