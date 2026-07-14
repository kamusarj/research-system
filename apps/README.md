# Applications

All deployable application code lives in this directory.

## Modules

- `api/`: FastAPI service. HTTP routers live in `app/api`, domain/application logic in `app/services`, request and response contracts in `app/schemas`, and persistence in `app/models.py` plus `migrations/`.
- `web/`: Next.js App Router client. Routes live in `app`, reusable UI in `components`, and API contracts/client helpers in `lib`.

## Dependency direction

```text
web -> /api/v1 HTTP contract -> api -> PostgreSQL
```

The web app does not import API internals. Search and graph remain rebuildable projections of the API's primary database. Shared runtime orchestration stays at the repository root so `docker compose` and `make` remain stable entrypoints.

## Naming convention

Use deployable-service names (`api`, `web`) for directories and Compose services. Add future deployables such as workers under `apps/`; add reusable, non-deployable code under a root `packages/` directory only when real cross-application reuse appears.
