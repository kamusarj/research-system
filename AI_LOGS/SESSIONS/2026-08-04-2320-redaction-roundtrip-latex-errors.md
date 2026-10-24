# Session: Preserve Redacted Values and Diagnose LaTeX

## User Request

Investigate and fix the next failure shown in Document Preview after the AI repaired a LaTeX CV.

## Files Changed

- `apps/api/app/services/graph_chat.py`
- `apps/api/app/services/document_instant_edit.py`
- `apps/api/app/services/latex_compiler.py`
- `apps/api/tests/test_graph_chat.py`
- `apps/api/tests/test_document_instant_edit.py`
- `apps/api/tests/test_latex_compiler.py`
- `apps/web/e2e/document-upload.spec.ts`
- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-redaction-roundtrip/`
- `docs/decisions/0035-reversible-document-edit-redaction.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`
- `AI_LOGS/DECISIONS.md`

## Decisions Made

- Keep sensitive originals out of provider input while restoring them exactly inside API memory.
- Require every selected-source token once and reject all marker leakage or mutation.
- Keep generic irreversible redaction for advisory chat only.
- Return bounded compiler line/reason without paths or source lines.

## Commands/Tests Run

- Harness bootstrap, intake #52, intervention #20, decision 0035, story completion and detailed
  trace #57.
- Reproduced `[REDACTED_PHONE]` as XeLaTeX `Missing $ inserted`.
- Focused backend tests: 35 passed.
- Full backend tests: 312 passed.
- Ruff lint and focused format: passed.
- Live compile through frontend proxy: typed `Line 1: Missing $ inserted.`.
- Real DeepSeek synthetic contact round trip: HTTP 200 in 7.4 seconds; originals absent from prompt,
  restored in response, no marker leakage, standalone and review-only.
- ESLint and TypeScript: passed.
- Document Playwright: 18 passed across desktop/tablet/mobile, including live safe compiler detail.
- Direct/proxied health and API reload logs: clean.

## Verification Result

Pass. Future cloud edits preserve local sensitive values without exposing them to the provider, and
invalid redaction output cannot reach review or Raw. Compiler failures now identify a safe line and
reason.

## Known Issues

- The current browser draft in the screenshot already contains placeholders, so the original email
  and phone are no longer available to the ephemeral request map. They must be restored manually
  from the original CV or another trusted copy before recompiling.

## Next Best Action

- Replace `[REDACTED_PHONE]` and `[REDACTED_EMAIL]` in the current Raw draft with the real trusted
  values, then let Preview recompile. Any remaining error will now report its line and reason.
