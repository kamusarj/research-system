# Validation

## Proof Strategy

Prove the original/derivative separation at the storage and API boundaries, then prove the browser
shows the disclosure, original access and editable content without regressing source formats.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Binary/current-version source resolution and safe preview metadata. |
| Integration | PDF/DOCX original bytes survive manual edit and restore; derivative reprocesses as text; unreadable binary stays locked. |
| E2E | Document detail exposes original access, disclosure and editor for a binary upload. |
| Platform | Rebuilt API/frontend serve the flow on `18000`/`13000`. |
| Performance | Existing upload/extract/editor size bounds remain enforced. |
| Logs/Audit | Version audit contains metadata only; fresh runtime logs contain no error signature. |

## Fixtures

- Minimal deterministic PDF with a readable text layer.
- Bounded DOCX OpenXML fixture.
- Existing Markdown editable-source fixture.

## Commands

```text
cd apps/api && PYTHONPATH=. .venv/bin/pytest -q && .venv/bin/ruff check app tests
cd apps/web && npm test -- --run && npm run lint && npx tsc --noEmit && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts --output /tmp/business-ai-harness-doc-e2e-20260809
```

## Acceptance Evidence

- Backend: 313/313 full tests and 23/23 focused document tests pass; Ruff passes.
- Frontend: 118/118 Vitest tests, ESLint, TypeScript and the 14-route production build pass.
- E2E: 21/21 Document Playwright cases pass across desktop, tablet and mobile, including a PDF
  original-preview/edit/save flow and the updated focus-window regression cases.
- Runtime: API/worker/frontend were recreated on `18000`/`13000`; readiness is `ready`, graph
  invariants are valid at 45 nodes / 32 edges, and a real existing DOCX renders a 40,222-character
  editor with derivative disclosure, original link and zero page-level horizontal overflow.
- Storage/API: integration proof keeps DOCX original bytes and attachment object key unchanged after
  manual edit, reprocesses the UTF-8 derivative, restores version 1 into a new derivative, and keeps
  original/download responses byte-identical.
