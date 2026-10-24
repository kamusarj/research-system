# Validation

## Proof Strategy

Prove the upload-to-isolated-graph path at the worker/service boundary, including a readable low-fit
document. Prove AI research schema validation, source-vs-AI comparison, idempotent governed
change-set creation and no direct canonical mutation. Prove relationship/hierarchy node parity and
the separate system map through API tests, then exercise the browser entry points and node inspector.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Summary bounds; AI research prompt/result IDs, bounds and comparison states; hierarchy derivation. |
| Integration | Low-fit upload graph; node/all research persistence; draft change set only; relationship/hierarchy parity; system endpoint. |
| E2E | View analysis link; graph node selection; summary/AI/difference panels; research-and-propose action; relationship/hierarchy/system navigation. |
| Platform | Migration head, production images, four-service Compose runtime, direct/proxied health. |
| Performance | Relationship response bounded at 1,000 nodes; research call bounded at 80 nodes and 50,000 source characters. |
| Logs/Audit | No document body, provider response or research text in audit/runtime logs. |

## Fixtures

- Deterministic readable low-fit document.
- Deterministic document graph and independent research provider outputs.
- Approved relationship corpus with canonical matches, parent links and research relations.
- Owner/researcher/viewer principals from existing fixtures.

## Commands

```text
cd apps/api && uv run ruff check <changed files> && uv run ruff format --check <changed files>
cd apps/api && uv run python -m pytest -q <focused tests>
cd apps/api && uv run python -m pytest -q
cd apps/web && npm run lint && npx tsc --noEmit && npm run test -- --run
cd apps/web && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npm run test:e2e
docker compose up -d --build database api worker frontend
```

## Acceptance Evidence

- Backend focused integration: 31 tests passed across document processing/research, graph changes,
  relationship/hierarchy and ontology/system projection.
- Backend full suite: 316 tests passed; Ruff lint passed and all 13 task-touched Python files passed
  `ruff format --check`.
- Frontend: ESLint and TypeScript passed; full Vitest suite passed 123 tests in 30 files; production
  Next.js build completed with 15 routes including `/graph/system`.
- Browser proof: focused desktop Playwright passed the `View analysis` deep-link and separate Business
  AI Agents system-map route (2 tests).
- Runtime: Compose rebuilt and kept PostgreSQL, API, worker and frontend running; Alembic reports
  `2d4e6f8a0b13 (head)` and `/api/v1/system/readiness` reports `ready` with valid graph invariants.
- Runtime projection parity: relationship and hierarchy each returned the same 429-node ID corpus;
  relationship had 370 edges, derived hierarchy 79 edges, and the separate system map had 45 nodes
  and 44 edges. Runtime accepted the configured 1,000-node/4,000-edge bounds.
- Runtime document inspection found an existing isolated graph and no serialized node summary over
  200 characters. Deterministic integration proof enforces a supported semantic summary in the
  requested 150–200-character range.
- API integration proves AI research records a `different` comparison and prepares a draft change
  set without changing canonical `KnowledgeNode` count.
