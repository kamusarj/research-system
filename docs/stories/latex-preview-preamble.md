# Safe LaTeX Preview Body Rendering

## Status

implemented

## Lane

normal

## Product Contract

The browser-safe LaTeX preview displays document body content, not package declarations or visual
formatting setup from the preamble. When a source includes `\\begin{document}` and
`\\end{document}`, Preview renders only the content between them. It remains an intentionally safe
markup preview, not a TeX compiler or PDF renderer.

## Relevant Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/editable-document-workspaces.md`

## Acceptance Criteria

- LaTeX preamble commands do not appear as preview prose.
- Headings, list items and simple text formatting in the document body remain readable.
- Raw still exposes the original source exactly.
- No TeX process or external package download is added to runtime.

## Design Notes

- Frontend-only parser correction.
- Actual TeX compilation/PDF rendering is out of scope because the stack contains no TeX engine and
  must not execute user-provided LaTeX in the API container.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Full-document LaTeX fixture hides the preamble and renders the body. |
| Integration | Not applicable. |
| E2E | Existing document preview suite remains responsive. |
| Platform | Desktop/tablet/mobile preview stays within viewport. |
| Release | ESLint, TypeScript, frontend tests and production build. |

## Harness Delta

None.

## Evidence

- Unit fixture verifies a XeLaTeX-style document renders only the `document` body and hides comments,
  package/font/color setup and preamble commands.
- Live Chrome visual proof confirms the preview contains the ALOHA heading/body but none of
  `XeLaTeX`, `usepackage` or `setmainfont`.
- ESLint, TypeScript, 101 frontend tests, the 14-route build and 9/9 document Playwright cases pass.
