# Document Preview Canvas

## Status

implemented

## Lane

normal

## Product Contract

Raw source shown below `Preview document` remains constrained to its own scrollable pane, including
long unbroken lines. The rendered preview becomes a larger, paper-like reading canvas inspired by
Overleaf: a centered white page on a subtle workspace background, with generous typography and
vertical reading space. Split mode prioritizes the preview width; preview-only mode remains centered
and readable. Tablet and mobile stack safely without horizontal overflow.

## Relevant Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-ai-edit-reliability/`

## Acceptance Criteria

- Raw source never expands the page horizontally; it scrolls within its own pane.
- Preview has a larger paper canvas and visibly receives more width in split mode.
- The same preview treatment applies to authoring and uploaded editable-source views.
- Preview stacks cleanly at tablet/mobile widths.

## Design Notes

- UI-only CSS and markup wrapper change; no API, AI provider, persistence, version, RAG or graph
  behavior changes.
- Reuse `DocumentPreview` rendering and existing safe source handling.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Document source viewer continues to render safe Raw/Preview/Split modes. |
| Integration | Not applicable: no API or persistence change. |
| E2E | Preview disclosure and document interaction suite across viewport projects. |
| Platform | Desktop/tablet/mobile no-horizontal-overflow check. |
| Release | ESLint, TypeScript, frontend tests and production build. |

## Harness Delta

None.

## Evidence

- Component proof confirms safe Raw/Preview/Split switching and the paper canvas wrapper.
- A live Chrome proof inserted a 12,000-character unbroken Raw line at desktop, tablet and mobile:
  the page had no horizontal overflow and Raw scrolled inside its own pane.
- ESLint, TypeScript, 100 frontend tests, the 14-route build and 9/9 document Playwright cases pass.
