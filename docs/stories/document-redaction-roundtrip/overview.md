# Overview

## Current Behavior

Document instant edit sends contact details to cloud providers as generic placeholders such as
`[REDACTED_PHONE]`. A provider can copy those placeholders into `replacement_text`; review then
permits them to replace the real local values. In LaTeX, their unescaped underscores also cause a
compile failure whose UI message currently omits the useful line and error category.

## Target Behavior

Use unique provider-only redaction tokens and restore their original local values before validating
or returning a patch. Any generic or unrestored redaction marker fails closed and cannot reach
Proposed/Raw. LaTeX compilation failures expose a bounded safe `Line N: reason` message.

## Affected Users

- Owners and researchers editing documents containing contact details or credentials.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-latex-edit-integrity/`
- `docs/stories/latex-overleaf-preview/`

## Non-Goals

- Recovering contact values already overwritten in an existing browser draft.
- Sending unredacted sensitive values to cloud providers.
- Automatically applying or saving repaired patches.
