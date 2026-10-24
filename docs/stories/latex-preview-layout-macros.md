# Safe LaTeX CV Layout Preview

## Status

implemented

## Lane

normal

## Product Contract

The safe LaTeX Preview hides common CV layout macros in the document body while retaining visible
text. `\\sidesection{…}` renders as a heading; font, color, spacing, minipage, alignment and page
layout commands do not become preview prose.

## Relevant Product Docs

- `docs/stories/latex-preview-preamble.md`

## Acceptance Criteria

- CV section headings and visible text render cleanly.
- `sidesection`, `fontsize`, `selectfont`, `color`, spacing and minipage commands do not display.
- Raw still shows the untouched LaTeX source.
- No TeX compiler/subprocess is added.

## Design Notes

- Browser parser only; intentionally bounded to safe readable text conversion.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | CV LaTeX macro fixture keeps visible content and hides layout syntax. |
| Integration | Not applicable. |
| E2E | Existing document preview suite remains responsive. |
| Platform | Browser visual proof with owner-style CV source. |
| Release | ESLint, TypeScript, frontend tests and production build. |

## Harness Delta

None.

## Evidence

- Unit fixture verifies common CV layout macros are removed while heading and visible text remain.
- Browser proof imports an owner-style LaTeX CV at 1920px: Preview contains only readable section
  text and no `sidesection`, font, spacing, minipage or alignment commands.
- ESLint, TypeScript, 102 frontend tests, the 14-route production build and 12 document Playwright
  cases pass across desktop, tablet and mobile.
