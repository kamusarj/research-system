# Validation

## Automated

- `cd apps/web && npm test -- --run document-brainstorm document-authoring document-ai-editor document-instant-edit`
- `cd apps/web && npm run lint`
- `cd apps/web && npx tsc --noEmit`
- `apps/api/.venv/bin/pytest apps/api/tests/test_document_brainstorm.py apps/api/tests/test_document_instant_edit.py -q`

## Acceptance

- Chat edit command shows `documentChatEditReady` and a pending Accept/Reject patch.
- Failed LaTeX-prose whole-source patch shows `documentChatEditFailed` and no Accept.
- Append of advisory prose into standalone LaTeX is blocked with
  `documentBrainstormLatexApplyBlocked`.
- Stale selection ranges are normalized away before edit/apply.
- Local status messages never enter brainstorm provider history.
