# True LaTeX PDF Preview

## Current Behavior

LaTeX Preview uses a bounded browser text parser. It cannot reproduce custom commands, TikZ,
fonts, geometry or page layout and therefore diverges from Overleaf.

## Target Behavior

LaTeX source is compiled by XeLaTeX and the resulting PDF is embedded in the existing paper
workspace. While compilation is pending or unavailable, the safe text renderer remains an explicit
fallback with a compilation status/error.

## Affected Users

- Owners and researchers authoring or editing LaTeX documents.

## Affected Product Docs

- `docs/stories/latex-preview-preamble.md`
- `docs/stories/latex-preview-layout-macros.md`

## Non-Goals

- Multi-file projects, uploads referenced by `includegraphics`, package downloads or shell escape.
