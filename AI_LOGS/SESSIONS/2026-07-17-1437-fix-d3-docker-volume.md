# Session Log

## Context

- User request: Fix the `/graph` build error shown in the browser: `Module not found: Can't resolve 'd3'`.
- Agent: Codex.
- Date/time: 2026-07-17 14:32-14:37 +07.

## Work Done

- Files changed: `docker-compose.yml`, `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.
- Behavior changed: frontend startup now validates top-level packages in the mounted `node_modules` volume and runs `npm install --no-audit --no-fund` only when dependencies are incomplete, before starting Next.js.
- Commands run: inspected package/lock/Compose state and frontend logs; checked `npm ls d3`; validated Compose; rebuilt/recreated frontend; rechecked D3, `/graph`, logs, TypeScript, and Vitest.

## Reasoning / Decisions

- Decision: keep the named `frontend_modules` volume, but make startup repair it when package dependencies change.
- Reason: the source bind mount needs a separate container-side `node_modules`; named volumes persist across image rebuilds and can therefore lag behind `package.json`. A conditional sync preserves fast normal restarts while preventing stale dependencies.
- Alternatives considered: deleting the volume would fix this instance but lose the safeguard for future dependency additions; always running `npm install` would add unnecessary work and network exposure to every restart.

## Verification

- Tests/checks: `docker compose config -q`; runtime `npm ls d3 --depth=0`; `GET http://localhost:13000/graph`; frontend compilation logs; `npm run typecheck`; `npm test`; a second frontend restart followed by another `/graph` request.
- Result: Compose is valid; runtime reports `d3@7.9.0`; `/graph` compiles 2,039 modules and returns HTTP 200 without module errors; TypeScript passes; all 5 test files and 12 tests pass. The follow-up restart skipped dependency installation because the volume was complete, and `/graph` still returned HTTP 200.

## Next Agent Notes

- Continue from: healthy graph workspace at `http://localhost:13000/graph`.
- Watch out for: the first frontend restart after adding/removing a package may run a dependency sync; subsequent complete-volume restarts skip it. Keep the PostgreSQL and unrelated `smart_exam_*` containers untouched.
- Suggested next command: `docker compose logs --since 2m frontend` if a future dependency-related browser overlay appears.
