# Validation

## Proof Strategy

Use deterministic provider doubles to prove the one-retry boundary and unchanged terminal error,
then repeat one real Mistral document-graph run against a non-sensitive fixture. Regression proof
must cover document processing and paper-fit behavior.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Invalid first response recovers once; valid first response does not retry; invalid recovery remains typed failure. |
| Integration | Upload/process fixture reaches review with valid nodes/edges, or retains `AI_RESPONSE_INVALID` after the bounded attempt. |
| E2E | Existing document retry/review workflow remains unchanged. |
| Platform | API/worker rebuild and readiness remain healthy. |
| Performance | At most one additional provider request for the targeted validation failure. |
| Logs/Audit | Recovery event contains identifiers/outcome but no raw response, document text or secret. |

## Fixtures

- Deterministic invalid-then-valid and invalid-then-invalid provider responses.
- A non-sensitive Markdown document suitable for a live Mistral run.

## Commands

```text
cd apps/api && .venv/bin/ruff check app tests
cd apps/api && .venv/bin/pytest -q tests/test_documents.py tests/test_paper_fit.py
docker compose up -d --build api worker
curl --fail http://localhost:18000/api/v1/system/readiness
```

## Acceptance Evidence

- Ruff passes across `app` and `tests`.
- All 88 backend tests pass; the only warning is the known Starlette/httpx TestClient deprecation.
- Three focused cases prove no retry for a valid response, one same-provider recovery for an
  invalid→valid sequence, and unchanged `ValidationError` after invalid→invalid.
- Live Mistral workspace `c91507a7-d186-418c-9202-34220ec75dfd` completed on its first structured
  response at score `74.5` with 20 supported nodes, 14 edges and zero dangling endpoints. The live
  response did not need recovery, so the intermittent recovery branch remains deterministic-test
  evidence rather than a claimed live event.
- Rebuilt API/worker are healthy on API port `18000`; readiness is `ready` with canonical graph
  invariants valid at 45 nodes and 32 edges.
