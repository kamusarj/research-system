# Session: Overleaf-like document preview

## User Request

Fix Raw overflow below `Preview document` and make the rendered preview larger, like Overleaf.

## Files Changed

- `apps/web/app/globals.css`
- `apps/web/components/document-source-viewer.tsx`
- `apps/web/components/document-ai-editor.tsx`
- `apps/web/components/document-source-viewer.test.tsx`
- `docs/stories/document-preview-overleaf.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`

## Decisions Made

- Keep Raw source unwrapped and monospace, but guarantee horizontal/vertical scrolling inside its
  own bounded pane.
- Give preview 64% of split width and render it as a centered white paper canvas on a muted gray
  workspace.
- Reuse the same safe renderer and canvas in authoring and uploaded editable-source views.
- Stack at 1024px and below to preserve narrow viewport usability.

## Commands/Tests Run

- `./scripts/bootstrap-harness.sh`
- Harness intake #41, intervention #10 and active matrix query.
- Focused component tests — 16 passed.
- Live Chrome width proof with a 12,000-character unbroken Raw line at 1440px, 1024px and 390px —
  page fit and internal Raw scrolling passed at every viewport.
- `npm run lint` and `npm run typecheck` — passed.
- `npm run test -- --run` — 100/100 passed.
- `npm run build` — passed, 14 routes.
- Document Playwright suite on `13000` — 9/9 passed across desktop/tablet/mobile.
- `git diff --check` — passed.

## Verification Result

Implemented and verified. Raw no longer creates document-level horizontal overflow; preview is a
larger Overleaf-like reading canvas and remains responsive.

## Known Issues

- The saved workspace route had no runtime fixture available during visual inspection and stayed in
  Loading; the exact authoring Preview document surface was instead inspected with populated local
  draft content.
- Default API host port 8000 remains occupied by an unrelated project; browser proof used frontend
  port 13000 as documented.

## Next Best Action

The owner can open `Preview document`, select `Song song` or `Xem trước`, and review the larger
canvas directly. No database migration or rebuild is required because the running frontend dev
container bind-mounts the changed source.
