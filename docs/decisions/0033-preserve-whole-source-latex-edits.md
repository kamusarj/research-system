# 0033 Preserve Whole-Source LaTeX Integrity During AI Edits

Date: 2026-08-04

## Status

Accepted and implemented locally; strengthens decisions 0029 and 0032 without changing their
review-before-apply or routing boundaries.

## Context

The owner showed a contextual rename request whose provider response contained Vietnamese
explanation, Markdown headings and fenced LaTeX snippets. The response was range-correct, so the
existing patch review could Accept it as the entire Raw source even though it was no longer a
standalone compilable LaTeX document.

## Decision

When the edit selection covers a complete source that is already a standalone LaTeX document, the
replacement must also be a standalone LaTeX document. It must contain `\documentclass`,
`\begin{document}` and a terminal `\end{document}`; Markdown fences, non-comment prefaces, missing
boundaries, duplicate terminal boundaries and trailing commentary are invalid.

Enforce the invariant before the API returns a patch and repeat it in the browser before exposing
Accept. Noncompliant provider output fails closed through the existing typed invalid-response UX;
the local draft remains unchanged.

## Alternatives Considered

1. Trust stronger prompt wording alone: rejected because provider output is an untrusted boundary.
2. Compile every response before review: rejected because compilation is a separate, more expensive
   bounded operation and structural rejection covers the reported corruption path.
3. Require standalone structure for partial LaTeX selections: rejected because valid fragments may
   be plain text, commands or environments rather than complete documents.

## Consequences

Positive:

- Explanatory AI prose cannot replace a valid complete LaTeX Raw source.
- Valid complete rename results retain the existing Original/Proposed Accept/Reject workflow.
- Backend and browser independently enforce the source-integrity invariant.

Tradeoffs:

- An otherwise useful provider response with commentary outside the document is rejected and must
  be retried.
- Structural validation does not prove arbitrary semantic instructions; explicit review remains
  required.

## Follow-Up

- Keep real-provider and browser regression proof in the high-risk story validation record.
