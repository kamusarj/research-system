# Session: Safe LaTeX preview body rendering

## User Request

Fix the apparent LaTeX compilation error in Document Preview.

## Files Changed

- `apps/web/components/document-source-viewer.tsx`
- `apps/web/components/document-source-viewer.test.tsx`
- `docs/stories/latex-preview-preamble.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`

## Decisions Made

- Do not add an unrestricted TeX compiler to the API: the running API image has no XeLaTeX,
  pdfLaTeX or Tectonic, and executing user-provided LaTeX would require a separately designed,
  sandboxed compilation service.
- Correct the existing safe renderer: use only text between `\\begin{document}` and
  `\\end{document}`, ignore comments and non-content preamble commands, and preserve readable body
  headings/lists/simple formatting.
- Keep Raw source exact for editing and inspection.

## Commands/Tests Run

- `./scripts/bootstrap-harness.sh`
- Harness intake #43, intervention #12 and active matrix query.
- Checked API runtime for `xelatex`, `pdflatex` and `tectonic`: none is installed.
- Focused source viewer tests — 3 passed.
- `npm run lint` and `npm run typecheck` — passed.
- `npm run test -- --run` — 101/101 passed.
- `npm run build` — passed, 14 routes.
- Live Chrome XeLaTeX-style preview — heading/body shown; compiler comments and preamble absent.
- Document Playwright suite on `13000` — 9/9 passed.
- `git diff --check` — passed.

## Verification Result

Implemented and verified. Preview no longer presents LaTeX preamble as document content. It is a
safe visual preview, not a PDF compilation result.

## Known Issues

- True PDF compilation is not implemented. Adding it requires a separately sandboxed compiler,
  strict resource/network/file limits and a high-risk product decision.

## Next Best Action

Refresh `/documents`, select LaTeX source and open Preview document: only content inside the
`document` environment should appear on the paper canvas.
