# Validation

## Proof Strategy

Prove optimistic version and selection conflicts at the service/API boundary,
then prove automatic vector replacement without exposing draft research in
global search. Exercise the browser workflow from selection through proposal,
Accept, refresh restoration, version restore and visible RAG state.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Editable-format rules, cache key/parser/bounds, AI prompt/result bounds, source hash/range checks. |
| Integration | Upload version 1; save/restore; propose/accept/reject; stale conflicts; immutable objects; automatic vector upsert; approved-only global semantic filter. |
| E2E | Select text, request rewrite, inspect diff, accept, F5 restore, view version history/RAG status at three viewports. |
| Platform | Upgrade/downgrade/re-upgrade, production build, rebuilt API/worker/frontend and local object storage. |
| Performance | Source 2M chars, selection 20k, AI context/replacement, chunks/batches/version list all bounded. |
| Logs/Audit | No source/selection/replacement/provider response in audit or runtime logs. |

## Fixtures

- Deterministic Markdown/TXT sources and immutable local object storage.
- Deterministic structured edit provider and 1024-dimension embedding double.
- Owner, researcher and viewer principals.

## Commands

```text
cd apps/api && uv run ruff check <changed files> && uv run ruff format --check <changed files>
cd apps/api && uv run python -m pytest -q
cd apps/web && npm run lint && npx tsc --noEmit && npm run test -- --run
cd apps/web && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npm run test:e2e
```

## Acceptance Evidence

- Changed backend files pass Ruff and focused document/version/RAG/search/chat/migration coverage:
  55 tests.
- Full backend suite passes: 285 tests.
- Frontend ESLint, TypeScript, 83 Vitest cases and the 14-route production build pass.
- Responsive Playwright document proof passes 9/9 across desktop, tablet and mobile, including
  selected-text AI proposal plus explicit Accept.
- PostgreSQL migration `2d4e6f8a0b13` is live; three existing workspaces received immutable version
  1 metadata without copying or deleting source objects.
- API, worker and frontend images were rebuilt on ports `18000`/`13000`; direct/proxied health and
  frontend return HTTP 200 and fresh logs contain no new error/traceback entries.
- Runtime backup before migration: `/tmp/research-pre-document-ai-edit.dump`.
