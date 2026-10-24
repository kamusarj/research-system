# Wrap Raw Source in Document Preview

## Status

implemented

## Lane

normal

## Product Contract

Raw source below `Preview document` visually wraps every line to the pane width, including long
URLs, LaTeX commands and unbroken text. It preserves whitespace/newlines and remains vertically
scrollable, but never exposes a horizontal scrollbar.

## Relevant Product Docs

- `docs/stories/document-preview-overleaf.md`

## Acceptance Criteria

- Long Raw source lines wrap inside the pane.
- Raw source has no horizontal scrollbar or hidden text beyond the pane.
- The page stays within viewport width at desktop, tablet and mobile sizes.

## Design Notes

- CSS-only presentation correction; source bytes, parser, preview, API and persistence are unchanged.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Existing safe document source viewer test remains green. |
| Integration | Not applicable. |
| E2E | Browser long-line check plus document interaction suite. |
| Platform | Desktop/tablet/mobile no-horizontal-overflow proof. |
| Release | ESLint, TypeScript, frontend tests and production build. |

## Harness Delta

None.

## Evidence

- Live Chrome proved a long Vietnamese LaTeX source wraps inside Raw with no horizontal scrollbar
  at 1920px, 1024px and 390px; the document itself stayed within every viewport.
- ESLint, TypeScript, 100 frontend tests, the 14-route build and 9/9 document Playwright cases pass.
