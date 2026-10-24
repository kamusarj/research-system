# Design

## Domain Model

A reversible cloud redactor owns an ephemeral in-request map from unique opaque tokens to original
sensitive substrings. The map is never returned, persisted or logged. Provider output is restored
locally, then rejected if any generic or provider-only marker remains.

## Application Flow

1. Tokenize sensitive values across instruction, selected source and bounded context.
2. Tell the provider to preserve opaque tokens exactly.
3. Restore known tokens in the structured response inside the API process.
4. Fail closed on altered, invented or generic redaction markers.
5. Run existing source-format checks and return a review-only patch.
6. On compile failure, extract only the document line number and bounded compiler reason.

## Interface Contract

No shape changes. Leaked redaction markers map to existing `AI_RESPONSE_INVALID`. Existing
`LATEX_COMPILE_FAILED` now carries a more actionable safe message when XeLaTeX provides one.

## Data Model

No schema, persistence, audit or retention change.

## UI / Platform Impact

Valid patches show restored original contact values in Proposed. Invalid markers never expose an
Accept action. Preview can show `Line N: Missing $ inserted.` instead of a generic failure.

## Observability

Only error codes, operation and timing remain logged; source, token map and compiler source lines are
excluded.

## Alternatives Considered

1. Escape generic placeholders for LaTeX: rejected because it still destroys the real local value.
2. Send contact values unredacted: rejected by the existing privacy boundary.
3. Blindly replace generic markers positionally: rejected because repeated types are ambiguous.
