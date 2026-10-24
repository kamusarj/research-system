# Validation

## Proof Strategy

Prove typed provider output, redaction, bounds, risk classification and zero persistence at the API
boundary. Prove client-side stale-response rejection, direct replacement, review-only protection,
Undo and unchanged explicit Save through unit/component and browser tests.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Range validation; risk detection; source revision echo; patch apply/undo/conflict helpers. |
| Integration | Redacted bounded provider prompt; no DB rows; no tools; no-change/provider errors. |
| E2E | Select prose → instant fix → Undo; stale response does not apply; protected source requires Apply; Save remains separate. |
| Platform | Selection/action/change bar at 1920, 1366, tablet and mobile; zero horizontal overflow. |
| Performance | 2M source, 20k selection, 40k replacement and bounded adjacent context. |
| Logs/Audit | No source/selection/instruction/replacement body in logs or audit rows. |

## Fixtures

- Deterministic structured provider replacement.
- Plain prose selection and citation/number/LaTeX selection.
- Delayed provider response followed by a local source edit.
- Owner/researcher/viewer document states.

## Commands

```text
cd apps/api && uv run ruff check app tests && uv run python -m pytest -q
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts
```

## Acceptance Evidence

- API quality gate passed: Ruff and all 294 backend tests.
- Web quality gate passed: ESLint, TypeScript, all 94 frontend tests and the 14-route production
  build.
- Focused API proof passed 19 tests across structured instant edits and document authorization;
  the instant-edit module itself covers bounded/redacted prompts, no persistence, protected-content
  classification, schema validation and rate limiting.
- Component proof covers local replacement, Undo, protected-content review, local cache updates and
  rejection of a provider response after the source changes.
- Playwright passed 9/9 document cases across desktop, tablet and mobile, including a native
  selection gesture, direct Improve replacement, Undo, unchanged explicit Save and zero horizontal
  overflow.
- Rebuilt API, worker and frontend are running on `18000` / `13000`; direct and proxied health are
  `ok`, readiness is `ready`, the canonical graph remains valid at 45 nodes / 32 edges, the new
  OpenAPI path is present and the recent API/worker/frontend error scan is clean.
- `git diff --check` passed.
- Harness story completion reran the complete proof command successfully; detailed trace #44 meets
  the high-risk tier 3/3 requirement.
