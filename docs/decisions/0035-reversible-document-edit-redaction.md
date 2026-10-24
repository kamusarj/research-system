# 0035 Use Reversible Redaction for Cloud Document Edits

Date: 2026-08-04

## Status

Accepted and implemented locally; strengthens decisions 0029 and 0033.

## Context

Generic cloud redaction placeholders were safe for provider input but unsafe as document output. A
provider copied `[REDACTED_PHONE]` and `[REDACTED_EMAIL]` into a reviewed whole-source LaTeX patch,
destroying the local contact values and introducing unescaped underscores that broke compilation.

## Decision

For document instant edits, replace each sensitive substring with a unique ephemeral provider-only
token. Keep the token-to-original map only in request memory, require every selected-source token
exactly once in provider output, restore originals before source-format validation, and reject any
generic, invented, altered, missing or duplicated marker.

Keep generic irreversible redaction for advisory graph chat, where output does not replace source.
Extract bounded XeLaTeX file-line diagnostics without returning compiler source lines or paths.

## Alternatives Considered

1. Escape generic placeholders: rejected because contact values would still be lost.
2. Send originals to the provider: rejected because it weakens the accepted privacy boundary.
3. Positionally restore generic placeholders: rejected because repeated values/types are ambiguous.

## Consequences

Positive:

- Sensitive values remain absent from cloud prompts and byte-faithful in reviewed patches.
- Redaction artifacts cannot enter Raw source.
- Compile failures identify a safe line number and reason.

Tradeoffs:

- Providers that alter or omit opaque tokens produce a typed invalid response and require Retry.
- Values already overwritten in an existing browser draft cannot be recovered from an ephemeral map.

## Follow-Up

- The owner must restore already-lost contact values from the original CV or another trusted copy.
