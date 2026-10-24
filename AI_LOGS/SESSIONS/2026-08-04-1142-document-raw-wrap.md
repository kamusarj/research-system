# Session: Wrap Raw document preview source

## User Request

Raw source below `Preview document` was still horizontal in the visual result.

## Files Changed

- `apps/web/app/globals.css`
- `docs/stories/document-preview-raw-wrap.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`

## Decisions Made

- Preserve Raw source characters and newlines, while visually wrapping long lines to the pane width.
- Hide horizontal overflow only after adding safe arbitrary-word breaks, so source is not clipped.
- Keep vertical scrolling for long source documents.

## Commands/Tests Run

- `./scripts/bootstrap-harness.sh`
- Harness intake #42, intervention #11 and active matrix query.
- Focused document source viewer tests — 2 passed.
- `npm run lint` and `npm run typecheck` — passed.
- `npm run test -- --run` — 100/100 passed.
- `npm run build` — passed, 14 routes.
- Live Chrome LaTeX proof at 1920px, 1024px and 390px — Raw and page widths fit with no horizontal
  scrollbar; visual screenshot confirmed wrapping.
- Document Playwright suite on `13000` — 9/9 passed.
- `git diff --check` — passed.

## Verification Result

Implemented and verified. Raw source has no horizontal scrollbar and no clipped long-line content;
the larger Preview paper canvas remains intact.

## Known Issues

- Default API host port 8000 remains occupied by an unrelated project; browser proof used frontend
  port 13000 as documented.

## Next Best Action

Refresh the existing `/documents` page and open `Preview document`; the Raw pane should now wrap
the LaTeX shown in the owner screenshot.
