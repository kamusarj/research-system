# US-LATEX-PREVIEW-DISPLAY-FIX Fix LaTeX Preview Display

## Status

implemented

## Lane

normal

## Product Contract

The Document workspace must show the latest compiled LaTeX page fitted inside the preview frame. After the source changes, the previous compiled PDF must disappear while the replacement is compiling so users never mistake stale output for the current draft.

## Relevant Product Docs

- `docs/stories/latex-overleaf-preview/overview.md`
- `docs/stories/latex-overleaf-preview/design.md`
- `docs/stories/document-uploaded-editing/design.md`
- `docs/decisions/0030-bounded-latex-compilation.md`
- `docs/decisions/0039-loss-safe-binary-document-editing.md`

## Acceptance Criteria

- Compiled LaTeX and uploaded PDF previews default to whole-page fitting rather than width fitting.
- Changing LaTeX source immediately removes the stale compiled iframe and shows the compiling fallback until the latest result arrives.
- Aborted compilation results cannot replace the latest preview and any discarded object URL is revoked.
- Existing bounded XeLaTeX compilation and immutable original-file behavior remain unchanged.

## Design Notes

- UI surface: `apps/web/components/document-source-viewer.tsx`.
- Use the browser PDF viewer's `view=Fit` fragment for whole-page framing.
- Keep the existing 450 ms compilation debounce and request cancellation.
- Do not infer or synthesize LaTeX from arbitrary uploaded PDFs.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-LATEX-PREVIEW-DISPLAY-FIX --unit 1 --integration 1 --e2e 1 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Viewer tests cover full-page PDF fragments and replacement preview lifecycle. |
| Integration | Typecheck and lint pass with the document viewer integration. |
| E2E | LaTeX document flow compiles and embeds a whole-page-fitted PDF. |
| Platform | Not required; no compiler or infrastructure change. |
| Release | Live workspace smoke check at the configured local frontend URL. |

## Harness Delta

Added a normal-lane story for a user-visible LaTeX preview regression. No harness workflow changes are required.

## Evidence

- `npm test -- --run components/document-source-viewer.test.tsx components/document-authoring.test.tsx components/document-ai-editor.test.tsx`: 32/32 passed.
- `npm run lint`: passed.
- `npx tsc --noEmit`: passed.
- `E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts --grep LaTeX --output /tmp/business-ai-latex-display-proof-20260809`: 9/9 passed across desktop, tablet and mobile Chrome.
- `scripts/bin/harness-cli story complete US-LATEX-PREVIEW-DISPLAY-FIX --json`: fresh verification passed and story moved to `implemented`.
- Harness trace #59 achieved the required standard tier 2/3 for this normal-lane story.
- Focused `git diff --check`: passed.
