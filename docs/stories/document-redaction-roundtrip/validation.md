# Validation

## Proof Strategy

Prove sensitive originals never enter provider prompts, known tokens restore locally, leaked or
altered markers fail closed, and compiler diagnostics reveal only a line number plus safe reason.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Unique tokenization, exact restoration, generic/altered marker rejection. |
| Integration | Instant-edit patch preserves email/phone; compile endpoint returns safe line reason. |
| E2E | Invalid response has no Accept and Raw remains unchanged. |
| Platform | Rebuilt API/frontend health and preview behavior. |
| Logs/Audit | No sensitive source/token-map/compiler source lines in logs. |

## Fixtures

- Two contact values of the same type.
- Whole-source LaTeX containing email and phone.
- `[REDACTED_PHONE]` compile failure.

## Commands

```text
cd apps/api && .venv/bin/python -m pytest -q tests/test_document_instant_edit.py tests/test_latex_compiler.py tests/test_graph_chat.py
cd apps/api && .venv/bin/python -m ruff check app tests
cd apps/web && npm run test -- --run && npm run lint && npm run typecheck && npm run build
```

## Acceptance Evidence

- Focused backend redaction/instant-edit/compiler/graph-chat tests pass 35/35. They prove unique
  tokens, exact selected-value restoration, missing/generic/invented marker rejection and safe
  compiler line extraction.
- Full backend tests pass 312/312; Ruff lint and focused Ruff format checks pass.
- Live compile through the frontend proxy turns the reported placeholder failure into
  `Line 1: Missing $ inserted.` without returning the source line or temporary path.
- A real DeepSeek whole-source LaTeX edit through `localhost:13000` returned HTTP 200 in 7.4
  seconds: synthetic email/phone were absent from provider input, restored in the review-only
  response, no `REDACTED` marker remained and standalone structure was preserved.
- ESLint and TypeScript pass. Document Playwright passes 18/18 across desktop, tablet and mobile,
  including the live compile endpoint rendering the safe line/reason while Raw stays unchanged.
- API hot reload completed cleanly; direct and proxied health remain `ok`.
