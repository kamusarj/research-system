# Validation

## Proof Strategy

Prove that explicit instructions are represented as mandatory provider requirements, every changed
response stays pending, Accept is the only local mutation path, Reject preserves source, identical
output maps to the no-change message, and stale responses cannot be accepted.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Prompt instruction priority; all patches review-only; exact no-change; patch conflict helpers. |
| Integration | Typed endpoint response; no DB rows; provider bounds/redaction unchanged. |
| Component | Changed output shows old/new; Accept mutates local draft; Reject preserves it; stale response is rejected. |
| E2E | Select text, request rewrite, review, Accept/Reject, explicit Save remains separate. |
| Platform | Diff and actions at desktop, 1366, tablet and mobile widths; no horizontal overflow. |
| Logs/Audit | No source/selection/instruction/replacement body in logs or audit rows. |

## Fixtures

- Deterministic custom conversion request and structured provider replacement.
- Identical provider replacement.
- Delayed provider response followed by a local source edit.
- Owner/researcher/viewer document states.

## Commands

```text
cd apps/api && uv run ruff check app tests && uv run python -m pytest -q
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts
```

## Acceptance Evidence

- API focused proof passes 7/7 tests, including mandatory whole-selection LaTeX output, exact
  no-change handling, revision-bound patches, redaction, no persistence and rate limiting.
- Ruff passes for the complete backend and all 296 backend tests pass.
- ESLint, TypeScript, 100/100 frontend tests and the 14-route production build pass.
- Component proof shows complete original/replacement content, no pre-Accept mutation, explicit
  Accept, explicit Reject and stale-response rejection in both document editors.
- Playwright passes 9/9 document cases across desktop, tablet and mobile, including review before
  Accept and zero horizontal overflow.
- A real DeepSeek request first reproduced the false no-change failure. After the output contract
  correction, the same request returned HTTP 200 with a complete `documentclass` / `document`
  environment, `auto_apply_allowed=false`, and no durable mutation.
- `git diff --check` passes. Full-tree Ruff format-only check still reports 36 unrelated pre-existing
  files; both changed backend files pass the focused format check.
