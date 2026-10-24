# Overview

## Current Behavior

A contextual rename command targets the complete source when no native selection exists. For a
standalone LaTeX draft, the provider can return explanatory Markdown and isolated LaTeX snippets as
`replacement_text`. Because the patch is range- and revision-correct, the existing review accepts
that structurally invalid payload and can replace the complete Raw draft after Accept.

## Target Behavior

When a complete standalone LaTeX source is selected, only another standalone LaTeX document may
become a pending patch. Explanatory prose, Markdown fences, missing document boundaries and trailing
commentary fail closed as `AI_RESPONSE_INVALID`; the existing Raw draft remains unchanged. Valid
rename patches still show complete Original/Proposed content and change the draft only after Accept.

## Affected Users

- Owners and researchers editing LaTeX source documents.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-chat-edit-intent/`
- `docs/stories/document-ai-edit-review/`

## Non-Goals

- Deterministically rewriting arbitrary names without the configured AI provider.
- Compiling provider output as part of the edit request.
- Automatically accepting, saving or repairing a failed patch.
- Requiring a standalone document when the selected source was only a LaTeX fragment.
