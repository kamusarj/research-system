# Full Project Defect Sweep

## Context

- User request: Sweep the complete project once and fix its errors.
- Agent: Codex
- Date/time: 2026-08-24 23:52 Asia/Bangkok

## Work Done

- Files changed:
  - `Makefile`, `README.md`
  - `apps/web/Dockerfile`, `apps/web/package.json`, `apps/web/package-lock.json`
  - `apps/web/lib/package-scripts.test.ts`, `apps/web/e2e/document-upload.spec.ts`
  - `docker-compose.yml`, `docker-compose.multi-user.yml`
  - `scripts/verify_graph_multi_user.sh`
  - `docs/stories/full-project-defect-sweep-2026-08-24.md`
  - `docs/stories/frontend-dependency-security-2026-08-24/*.md`
  - `docs/decisions/0043-next15-maintenance-security-patch.md`
  - `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`
- Behavior changed:
  - Make targets use the Discord bot's own locked environment instead of the API environment.
  - TypeScript checks no longer write a cross-owner incremental cache from Docker.
  - Frontend images install strictly from the lockfile; local/production startup validates the
    complete dependency volume and deterministically resynchronizes it when stale.
  - Frontend runtime dependencies resolve to patched Next.js 15.5.23 and patched transitive versions.
  - The responsive document-edit E2E exercises the active modal editor rather than a covered
    background textarea after Undo.
- Commands run:
  - `scripts/bootstrap-harness.sh`, Harness intake/story/decision/query commands.
  - API and Discord Ruff/Pytest; frontend ESLint/TypeScript/Vitest/build.
  - Full and production `npm audit`, resolved-tree checks and frontend Docker build/recreate.
  - SQLite migration parity, live PostgreSQL head and graph invariants.
  - Base/multi-user/Discord Compose validation and Desktop autostart verification.
  - Live direct/proxied health, eleven route probes, container log scans.
  - Focused tablet Playwright plus the complete desktop/tablet/mobile suite.

## Reasoning / Decisions

- Decision: remain on patched Next.js 15.5 Maintenance LTS instead of performing an unrelated major
  migration; record this as Harness decision 0043 and `DEC-056`.
- Reason: it removes the current known audit findings with a smaller compatibility surface, while
  full application and runtime regression proves preserved behavior.
- Alternatives considered: Next.js 16 migration, accepting local-only transitive risk, forced npm
  audit upgrades and pruning Docker data to finish the very large API image rebuild. All were
  rejected for this bounded repair.

## Verification

- Tests/checks:
  - API: Ruff passed; 323 tests passed with one known upstream Starlette/httpx deprecation warning.
  - Discord: Ruff passed; 55 tests passed.
  - Frontend: ESLint and TypeScript passed; 33 files / 145 Vitest tests passed; Next.js produced all
    15 routes; both npm audits report zero vulnerabilities.
  - Browser: 69 enabled Playwright cases passed on desktop/tablet/mobile; six authentication cases
    were expected skips under local auth-disabled mode.
  - Data/runtime: migration parity and live head passed at `2d4e6f8a0b13`; graph invariants are valid
    at 45 nodes / 32 edges; eleven routes and direct/proxied health returned HTTP 200; autostart passed.
  - Isolation: the Business AI Agents API container and PostgreSQL/named volumes were preserved while
    only its frontend was rebuilt/recreated. The first post-recreate check showed every Smart Exam ID
    unchanged. Later final inspection found its frontend/backend independently recreated even though
    no command in this sweep targeted that Compose project; both are healthy with PostgreSQL and
    Chroma still on their original IDs.
- Result: requested sweep and reproducible fixes pass all available code, build, migration, browser,
  runtime and dependency gates.
- Harness: both stories completed; detailed security trace #2 and standard sweep trace #3 meet their
  lane requirements; drift audit entropy is 0/100.

## Known Issues

- The root filesystem remains 96% full. A full API Docker rebuild was stopped when its uncached
  TeX/OCR layer consumed most remaining space; no prune was authorized or run. The unchanged live API
  image and all API tests/runtime checks pass.
- Re-run the frontend audit after the announced 2026-08-26 Next.js security release becomes
  available.
- Six authentication Playwright cases require a separate auth-enabled runtime and are intentionally
  skipped in the trusted-local auth-disabled configuration.

## Next Agent Notes

- Continue from: healthy frontend `13000`, API `18000`, Smart Exam `8080`; autostart is active.
- Watch out for: do not prune Docker or delete volumes without owner authorization; root disk is
  nearly full.
- Suggested next command: `scripts/verify_local_autostart.sh && cd apps/web && npm audit`.
