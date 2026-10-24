# Session: Preserve LaTeX Raw During AI Rename

## User Request

Fix the Document workspace so a rename command edits the name inside Raw source instead of replacing
the source with explanatory prose like the supplied screenshot; verify the fix carefully.

## Files Changed

- `apps/api/app/services/document_instant_edit.py`
- `apps/api/tests/test_document_instant_edit.py`
- `apps/web/lib/document-instant-edit.ts`
- `apps/web/lib/document-instant-edit.test.ts`
- `apps/web/hooks/use-document-instant-edit.ts`
- `apps/web/components/document-authoring.test.tsx`
- `apps/web/e2e/document-upload.spec.ts`
- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-latex-edit-integrity/`
- `docs/decisions/0033-preserve-whole-source-latex-edits.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`
- `AI_LOGS/DECISIONS.md`

## Decisions Made

- Treat provider output as untrusted even after structured JSON validation.
- When the complete selected source is already standalone LaTeX, require the complete replacement
  to remain standalone LaTeX, unfenced and free of non-comment text outside document boundaries.
- Enforce the same invariant at the API and browser boundaries.
- Keep the existing review contract: valid output remains pending until Accept; no automatic save,
  RAG refresh or durable mutation was added.

## Commands/Tests Run

- `scripts/bootstrap-harness.sh`
- `scripts/bin/harness-cli query matrix --active --summary`
- Harness intake #50, intervention #18, decision 0033, story completion and detailed trace #55.
- Backend focused Pytest: 13 passed.
- Full backend Pytest: 307 passed.
- Ruff lint: passed; focused Ruff format check: passed after formatting the new test fixture.
- Full frontend Vitest: 109 passed.
- ESLint: passed.
- TypeScript: passed.
- Next.js production build: 14 routes passed.
- Playwright `e2e/document-upload.spec.ts`: 15 passed across desktop/tablet/mobile using a fresh
  `/tmp` output directory.
- Real DeepSeek request through `http://localhost:13000/api/v1/documents/edit-in-place`: HTTP success
  in 4.4 seconds; standalone LaTeX response contained `Bùi Hoàng Linh` and remained review-only.
- `git diff --check` on task files: passed.

## Verification Result

Pass. The reported explanatory response shape is rejected before review at both boundaries, no
Accept action is rendered and Raw stays unchanged. A complete valid rename remains reviewable and
the live configured provider returned the requested name inside standalone LaTeX source.

## Known Issues

- The repository `apps/web/test-results` directory is root-owned, so Playwright's default reporter
  could not update `.last-run.json`. Proof passed with a fresh `/tmp` output directory; repository
  permissions were intentionally not changed.
- Structural validation cannot prove every arbitrary semantic instruction; explicit human review
  remains required.

## Next Best Action

- Refresh `/documents` and retry the rename on the original CV. A malformed provider response will
  now show safe retry feedback without changing Raw; a valid response will show the complete source
  diff and requires Accept.
