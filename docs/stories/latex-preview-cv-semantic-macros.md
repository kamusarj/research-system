# Semantic LaTeX CV Preview

## Status

implemented

## Lane

normal

## Product Contract

The safe LaTeX Preview renders the common semantic CV commands used by the supported template as
readable content, never as raw source. `mainsection` becomes a primary section heading;
`jobheading` becomes a role plus date/employer line; `tightbullets` and `closebullets` control a
normal list without rendering themselves.

## Relevant Product Docs

- `docs/stories/latex-preview-layout-macros.md`
- `docs/stories/latex-preview-preamble.md`

## Acceptance Criteria

- CV section, role, time/employer and bullet text remain visible.
- `mainsection`, `jobheading`, `tightbullets` and `closebullets` never appear in Preview.
- Raw source remains unchanged.
- The renderer remains browser-only and does not compile TeX.

## Design Notes

- Explicit semantic mappings are safer and more useful than rendering unknown TeX commands.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Semantic CV macro fixture yields headings, metadata and bullet text without macro names. |
| Integration | Not applicable. |
| E2E | Import CV fixture and check Preview across Chrome projects. |
| Platform | Direct Chrome visual proof of the CV experience section. |
| Release | ESLint, TypeScript, frontend tests and production build. |

## Harness Delta

None.

## Evidence

- Unit fixture covers section, job and list mappings.
- Direct Chrome inspection of an owner-style CV work-experience section displays readable content
  only; all four macro names are absent.
- ESLint, TypeScript, 103 frontend tests, a 14-route production build and 12/12 document Playwright
  cases pass.
