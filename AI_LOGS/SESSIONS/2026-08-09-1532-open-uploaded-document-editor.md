# Session Log

## Context

- User request: Correct the claim that uploaded documents were editable because clicking an uploaded file did not open an editor.
- Agent: Codex
- Date/time: 2026-08-09 15:32 +0700

## Work Done

- Files changed:
  - `apps/web/app/documents/page.tsx`
  - `apps/web/app/documents/page.test.tsx`
  - `apps/web/e2e/document-upload.spec.ts`
  - `apps/web/lib/i18n.tsx`
  - `docs/stories/document-list-open-editor.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - `AI_LOGS/SESSIONS/2026-08-09-1532-open-uploaded-document-editor.md`
- Behavior changed:
  - Uploaded filenames now link directly to their existing document detail/editor workspace.
  - The row's primary action now says `Open document` / `Mở tài liệu` and reaches the same route.
  - Download and Research links retain their independent destinations.
- Commands run:
  - Harness bootstrap, intake #59 and story `US-DOCUMENT-LIST-OPEN-EDITOR` lifecycle commands.
  - A red Playwright regression run before implementation.
  - Full/focused Vitest, ESLint, TypeScript and full Document Playwright validation.
  - A real Chrome click-through against the existing DOCX in the live runtime.

## Reasoning / Decisions

- Decision: Repair discoverability/navigation at the list boundary instead of changing the editor or backend again.
- Reason: DOM inspection and a failing browser test proved the filename was plain `<strong>` text. The detail route already rendered editable extracted text correctly.
- Alternatives considered:
  - Wrapping the entire table row was rejected because the row already contains independent Download and Research links, which would create invalid nested interactive controls.
  - Adding a second editor on the list page was rejected because it would duplicate versioning, RAG and optimistic-concurrency behavior.

## Verification

- Tests/checks:
  - Red browser test: filename link absent before implementation.
  - `npm test -- --run`: 121/121 passed.
  - Focused post-change Vitest: 11/11 passed.
  - `npm run lint`: passed.
  - `npx tsc --noEmit`: passed.
  - Full `e2e/document-upload.spec.ts`: 24/24 passed across desktop/tablet/mobile.
  - Fresh Harness story completion: passed.
  - Live real-data Chrome proof: existing DOCX filename linked to its UUID route; editor was non-readonly with 40,222 characters and zero console errors.
- Result: The reported click path now reaches the editable workspace in both deterministic tests and the current runtime. Trace #60 meets standard tier 2/3; intervention #21 records the owner's correction.

## Known Issues

- A document that has not completed readable extraction still cannot expose an editor; its detail workspace shows processing or extraction failure state instead.
- PDF/DOCX edits remain extracted-text derivatives and do not rewrite the original binary layout.

## Next Agent Notes

- Continue from: frontend `http://localhost:13000/documents`, API `http://localhost:18000`; current document list navigation is live through the source-mounted frontend runtime.
- Watch out for: keep nested actions separate; do not make the whole row a link while Download/Research actions remain inside it.
- Suggested next command: `cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts`.
