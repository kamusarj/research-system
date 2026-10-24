# Validation

## Proof Strategy

Verify both useful telemetry and negative security properties: stable route-template
labels, request correlation, valid Prometheus exposition, authentication failure
modes, and absence of bodies, secrets, raw paths, and arbitrary logging fields.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Request-ID grammar; JSON allowlist; metric helper label normalization. |
| Integration | Response correlation; disabled/misconfigured/unauthorized/authorized scrape; route-template metrics. |
| E2E | Existing browser suite remains green. |
| Platform | API and worker images build; external scrape works against the Compose API with a temporary test secret. |
| Performance | Existing timing headers remain present; histogram records API latency. |
| Logs/Audit | JSON logs contain allowed correlation/outcome fields and exclude supplied secret/body markers; existing PostgreSQL audit tests remain green. |

## Fixtures

- Deterministic request IDs and invalid request-ID samples.
- An integration-only metrics bearer value that is never written to repository
  configuration or AI logs as a real credential.
- Existing deterministic provider doubles and graph fixtures.

## Commands

```text
cd apps/api && uv run pytest -q
cd apps/api && uv run ruff check app tests
cd apps/web && npm run test:e2e
docker compose build api worker
curl -H 'Authorization: Bearer <temporary-test-secret>' http://127.0.0.1:18000/metrics
```

## Acceptance Evidence

- `uv run ruff check app tests`: passed.
- `uv run python -m pytest -q`: 104 passed; one upstream TestClient deprecation warning.
- `E2E_BASE_URL=http://127.0.0.1:13000 npm run test:e2e`: 27 passed across
  desktop, tablet and mobile.
- `docker compose config --quiet && docker compose build api worker`: passed with
  `prometheus-client==0.25.0` installed in both images.
- Temporary enabled runtime proof returned 401 without a bearer value and 200 with the
  integration-only bearer. The scrape contained template labels for health, readiness and metrics,
  and the JSON runtime log preserved `request_id=runtime-proof-21` without raw URLs or content.
- The stack was restored to the secure default after proof: health 200, `/metrics` 404, readiness
  `ready`, 45 canonical nodes, 32 edges and zero invariant errors.
- The first E2E attempt used the default port 3000 while this host runs the project on 13000 and
  failed with connection refused. A second attempt overlapped the old API image after source reload
  and had nine API-dependent failures. After the rebuilt API/worker were recreated on the documented
  ports, the authoritative final run passed 27/27.
