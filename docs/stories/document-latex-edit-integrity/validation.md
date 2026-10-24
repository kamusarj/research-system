# Validation

## Proof Strategy

Prove that the exact class of explanatory provider output shown by the owner is rejected at both
server and browser boundaries, while a complete renamed LaTeX document remains reviewable and only
changes Raw after explicit Accept.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Standalone LaTeX detection; fenced, prefixed, truncated and trailing prose rejection. |
| Integration | Whole-source LaTeX API returns typed invalid response for explanatory prose. |
| E2E/component | Invalid patch never renders Accept or changes Raw; valid rename still does. |
| Platform | Authoring and uploaded-source editors use the same guarded hook. |
| Performance | No extra provider or compile request. |
| Logs/Audit | Existing typed provider outcome only; no source body logging. |

## Fixtures

- Standalone LaTeX CV containing `NGUYỄN MINH AN`.
- Reported-style Markdown explanation with fenced LaTeX snippets.
- Complete standalone replacement containing `BÙI HOÀNG LINH`.

## Commands

```text
cd apps/api && .venv/bin/python -m pytest -q tests/test_document_instant_edit.py
cd apps/api && .venv/bin/python -m ruff check app/services/document_instant_edit.py tests/test_document_instant_edit.py
cd apps/web && npm run test -- --run lib/document-instant-edit.test.ts hooks/use-document-instant-edit.test.ts components/document-authoring.test.tsx components/document-ai-editor.test.tsx
cd apps/web && npm run lint && npm run typecheck && npm run build
```

## Acceptance Evidence

- Backend focused instant-edit tests pass 13/13, including the reported explanatory Markdown
  response, valid complete rename, truncated source, fenced source, preface and trailing prose.
- Full backend tests pass 307/307; Ruff lint and focused Ruff format checks pass.
- Frontend component/unit proof passes 109/109. The browser boundary returns the localized
  incomplete-response error, exposes no Accept action and leaves Raw byte-for-byte unchanged.
- ESLint, TypeScript and the 14-route production build pass.
- Document Playwright passes 15/15 across desktop, tablet and mobile. Three new browser cases inject
  the reported malformed response and prove no review/Accept plus unchanged Raw.
- A real DeepSeek `deepseek-v4-pro` call through `localhost:13000` completed in 4.4 seconds with a
  standalone LaTeX replacement containing `Bùi Hoàng Linh`; `auto_apply_allowed` remained false.
- The first Playwright invocation could not write the root-owned `test-results/.last-run.json`.
  Re-running with a fresh `/tmp` output directory passed and did not alter repository permissions.
