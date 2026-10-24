# Session Log

## Context

- User request: Fix the Network graph because pointer hover still felt laggy.
- Agent: Codex
- Date/time: 2026-08-11 11:33 +0700

## Work Done

- Files changed:
  - `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`
  - `apps/web/app/globals.css`
  - `apps/web/e2e/graph-hierarchy.spec.ts`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `docs/stories/knowledge-graph-hover-paint-performance.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - Network hover changes only the pointed node/label or edge; it never toggles corpus-wide focus.
  - Click selection still dims unrelated nodes using the indexed adjacency/incident-edge projection.
  - Force layout is synchronously settled before display and remains stopped during pointer use.
  - Removed delayed fit animations, inherited graph-container cursor writes and SVG paint filters.
  - The responsive graph E2E now makes the hover-versus-click performance contract explicit.
- Commands run:
  - `scripts/bootstrap-harness.sh`
  - Harness intake/story/intervention/trace commands (intake #66, intervention #22, trace #67)
  - `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`
  - `npm run test:e2e -- e2e/graph-hierarchy.spec.ts`
  - `docker compose build frontend`
  - `FRONTEND_PORT=13000 docker compose up -d --no-deps frontend`
  - Live Playwright/Chrome forced-style, frame, long-task, transition and layout benchmark
  - Runtime graph/stats/readiness HTTP checks

## Reasoning / Decisions

- Decision: Keep pointer feedback local and reserve whole-network neighborhood isolation for click.
- Reason: The prior implementation removed D3 transitions and scans, but its hover root class still
  invalidated opacity across 799 SVG elements, so its JavaScript-only timing missed style/paint cost.
- Alternatives considered: Retaining whole-network hover with CSS-only dimming was rejected because
  it still repaints the corpus. A Web Worker layout was unnecessary after stopping background force
  ticks and delayed fit animations.

## Verification

- Tests/checks:
  - ESLint and TypeScript pass.
  - Vitest: 31 files / 136 tests pass.
  - Focused Harness verifier: 4 files / 34 tests and production build pass.
  - Playwright: desktop/tablet/mobile, 3/3 pass in about 8 seconds.
  - Live graph: 429 nodes / 370 edges; forced-style hover 0.068 ms average / 0.4 ms max; hover frame
    16.357 ms average / 16.8 ms max; zero post-switch long tasks, transition owners and browser
    errors; layout stable; corpus focus absent during hover.
  - `/graph`, proxied `/api/v1/graph/stats` and `/api/v1/system/readiness` return HTTP 200.
- Result: Passed. Rebuilt frontend is running on `http://localhost:13000/graph`; API stays on
  `http://localhost:18000`.

## Known Issues

- Switching into Network performs a one-time deterministic layout settle (measured at 581 ms on
  the 429-node dataset). This is outside steady-state hover and replaces multiple seconds of force
  and fit animation that previously competed with pointer input.
- The unrelated `smart_exam_backend` still owns host port 8000; Research System continues to use
  the documented API port 18000.

## Next Agent Notes

- Continue from: Runtime is healthy and ready for owner visual/interaction review.
- Watch out for: Do not reintroduce corpus-wide root state, transitions, filters or force restarts in
  Network mouseenter/mouseleave handlers.
- Suggested next command: `curl -fsS http://localhost:13000/api/v1/system/readiness`
