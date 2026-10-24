# US-FULL-PROJECT-DEFECT-SWEEP-2026-08-24 Sweep the complete project for reproducible defects

## Status

implemented

## Lane

normal

## Product Contract

Backend, frontend, supporting services, production builds, the local Compose runtime and primary
browser routes pass their available regression checks. Reproducible defects found during the sweep
are fixed without resetting persistent data or reverting unrelated worktree changes.

## Relevant Product Docs

- `Docs/Business AI Agents Completion Goal.md`
- `Docs/Research System Implementation Plan.md`
- `README.md`
- `Docs/Graph Intelligence v2 Operations Runbook.md`

## Acceptance Criteria

- Backend and Discord bot lint/tests pass in their supported environment.
- Frontend ESLint, TypeScript, Vitest and production build pass.
- Compose configuration, migrations, graph invariants, health/readiness and primary routes pass.
- Responsive Playwright coverage passes against the live `13000` runtime without browser errors.
- Every reproducible defect changed by this story receives focused regression proof.
- PostgreSQL, document volumes, Smart Exam `8080`, and unrelated worktree changes remain intact.

## Design Notes

- Run broad diagnostics before changing product code.
- Keep fixes bounded to reproducible failures and rerun the smallest focused check before the full
  regression suite.
- Escalate auth, authorization, migration, deletion, audit/security, or provider-contract changes
  into a focused high-risk story before implementation.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Complete backend, Discord bot and frontend unit suites. |
| Integration | Migration, Compose, API readiness and graph invariant checks. |
| E2E | Responsive Playwright suite against the live runtime. |
| Platform | Production build, service health, bind source and clean current logs. |
| Release | Smart Exam and persisted Business AI Agents data remain intact. |

## Harness Delta

No Harness policy change expected. Desktop Harness intake #2 records the owner-requested sweep.

## Evidence

- Backend Ruff passed; all 323 API tests passed with one known upstream Starlette/httpx deprecation
  warning. Discord Ruff and all 55 tests passed in its own locked environment.
- Frontend ESLint, non-incremental TypeScript, 33 Vitest files / 145 tests and the 15-route
  production build passed on Next.js 15.5.23.
- Responsive Playwright passed 69 enabled cases on desktop/tablet/mobile; six authentication cases
  were intentionally skipped because this trusted-local runtime has authentication disabled.
- SQLite migration upgrade/check/downgrade/upgrade parity and live PostgreSQL head passed at
  `2d4e6f8a0b13`; live graph invariants passed for 45 nodes and 32 edges with zero errors.
- Base, multi-user and Discord Compose configurations, the deterministic frontend image build,
  direct/proxied health, eleven primary routes and Desktop autostart verification passed.
- Recreating only the frontend preserved the Business AI Agents API container and PostgreSQL/named
  volumes. The scoped recreation initially preserved all Smart Exam IDs; its frontend/backend were
  independently recreated later in the session while no sweep command targeted that project.
  Smart Exam is healthy on `8080`; Business AI Agents is healthy on `13000` / `18000`.
- Fixes cover separate API/Discord development environments, non-incremental host/container
  TypeScript checks, lockfile-based Docker installs, stale dependency-volume synchronization and a
  modal-aware tablet E2E interaction.
- A full API image rebuild was deliberately stopped before completion when its uncached TeX/OCR
  layer drove the root filesystem to 96% usage. The unchanged live API image and all API code,
  migration and invariant checks pass; no data or Docker volume was pruned.
