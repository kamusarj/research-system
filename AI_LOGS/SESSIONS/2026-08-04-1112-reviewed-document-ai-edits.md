# Session: Reviewed document AI edits

## User Request

Change the document AI rewrite control so AI follows the user's instruction; report no change only
when there is genuinely no change, otherwise show old and new text with VS Code-style Accept or
Reject.

## Files Changed

- `apps/api/app/services/document_instant_edit.py`
- `apps/api/tests/test_document_instant_edit.py`
- `apps/web/hooks/use-document-instant-edit.ts`
- `apps/web/components/document-instant-edit-feedback.tsx`
- `apps/web/components/document-authoring.test.tsx`
- `apps/web/components/document-ai-editor.test.tsx`
- `apps/web/e2e/document-upload.spec.ts`
- `apps/web/lib/i18n.tsx`
- `Docs/Research System Implementation Plan.md`
- `docs/decisions/0027-local-instant-document-ai-patches.md`
- `docs/decisions/0029-review-every-document-ai-edit.md`
- `docs/stories/document-ai-edit-review/*`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`
- `AI_LOGS/DECISIONS.md`

## Decisions Made

- Every changed patch requires review and explicit Accept or Reject, regardless of risk.
- The draft cannot change while review is pending; Accept reruns conflict checks.
- Exact identical replacement text alone is a legitimate no-change result.
- Whole-source LaTeX requests require a verifiable standalone LaTeX document; noncompliant output
  is a typed invalid response rather than a false no-change.
- Create/Save remains the only durable version and RAG mutation boundary.

## Commands/Tests Run

- `./scripts/bootstrap-harness.sh`
- Harness intake #40, intervention #9, active matrix query, story and decision registration.
- `uv run python -m pytest -q tests/test_document_instant_edit.py` — 7 passed.
- `uv run python -m pytest -q` — all 296 backend tests passed.
- `uv run ruff check app tests` — passed.
- Focused Ruff formatting for both changed backend files — passed.
- `npm run lint` and `npm run typecheck` — passed.
- `npm run test -- --run` — 100/100 passed.
- `npm run build` — passed, 14 routes.
- Playwright document suite on `13000` — 9/9 passed across desktop/tablet/mobile.
- Real DeepSeek bounded LaTeX smoke on `18000` — initial 409 reproduced; corrected request returned
  HTTP 200 with standalone LaTeX and `auto_apply_allowed=false`.
- `git diff --check` — passed.

## Verification Result

Implemented and verified. Both document editors show complete old/new content before mutation,
Accept applies only to the local revision-bound draft, Reject preserves source, and runtime
DeepSeek follows the enforced whole-source LaTeX contract.

## Known Issues

- Full-tree `ruff format --check app tests` reports 36 unrelated pre-existing files. The two backend
  files changed in this session pass focused formatting.
- Default host port 8000 remains occupied by an unrelated project; runtime proof used the documented
  API 18000 / frontend 13000 override.

## Next Best Action

The owner can repeat the original document selection and LaTeX request, compare the complete diff,
then Accept or Reject. No database migration or rebuild is required because the running dev stack
bind-mounts the changed source.
