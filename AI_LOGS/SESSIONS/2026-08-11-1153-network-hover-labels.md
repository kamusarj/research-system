# Session Log

## Context

- User request: Remove inconsistent always-visible Network node names; hide every name until the
  pointer is over that node, while retaining faint dashed connections.
- Agent: Codex
- Date/time: 2026-08-11 11:53 +0700

## Work Done

- Files changed:
  - `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`
  - `apps/web/e2e/graph-hierarchy.spec.ts`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `docs/stories/knowledge-graph-hover-labels.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - All Network labels/backdrops are opacity zero at rest, independent of importance, rank, degree,
    zoom or selection.
  - Local mouse hover or keyboard focus reveals exactly the current node label/backdrop.
  - Click neighborhood focus still emphasizes nodes/edges but no longer makes selected or ranked
    neighbor labels visible; leaving the node restores zero visible names.
  - Network overview edges remain `0.08`-opacity dashed lines and direct incident edges reveal on
    hover. Hierarchy and Orbit label/edge behavior is unchanged.
- Commands run:
  - `scripts/bootstrap-harness.sh`
  - Harness intake/intervention/story/trace commands (intake #68, intervention #23, trace #69)
  - `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`
  - `npm run test:e2e -- e2e/graph-hierarchy.spec.ts`
  - `docker compose build frontend`
  - `FRONTEND_PORT=13000 docker compose up -d --no-deps frontend`
  - Live Playwright/Chrome label-count and screenshot proof
  - Runtime `/graph` and readiness checks

## Reasoning / Decisions

- Decision: Remove Network semantic-rank label visibility entirely.
- Reason: Showing labels only for important nodes was technically bounded but visually inconsistent;
  one uniform hover-only rule makes the dense overview predictable and much cleaner.
- Decision: Click selection must not reveal a group of labels.
- Reason: The owner explicitly requested names only when the pointer is over a node; click continues
  to communicate structure through node/edge focus without violating that rule.
- Alternatives considered: Keeping a small permanent hub-label budget was rejected as the source of
  the inconsistency. Applying hover-only labels to Hierarchy was rejected because card text is the
  navigation model there; Orbit remains a separate bounded overview.

## Verification

- Tests/checks:
  - ESLint and TypeScript pass.
  - Vitest: 31 files / 136 tests pass.
  - Focused Harness verifier: 4 files / 34 tests and production build pass.
  - Playwright desktop/tablet/mobile: 3/3 pass, asserting zero rest labels, one hover label, zero
    leave labels, zero click-away labels and unchanged faint/revealed edge semantics.
  - Live 429-node / 370-edge runtime: zero resting labels, one hovered label at opacity 1, zero
    selected-away labels, overview edges opacity `0.08` / dash `3px, 7px`, 68 revealed incident
    edges for the highest-degree node and zero browser errors.
  - `/graph` and proxied `/api/v1/system/readiness` return HTTP 200; readiness is valid.
- Result: Passed. Rebuilt frontend is live at `http://localhost:13000/graph`.

## Known Issues

- The toolbar still includes the existing `Labels` control used by Orbit. In Network, the owner's
  hover-only rule takes precedence, so it cannot expose permanent overview labels.
- The unrelated `smart_exam_backend` owns host port 8000; Research System continues on API 18000.

## Next Agent Notes

- Continue from: Runtime is healthy and ready for owner review.
- Watch out for: Do not reintroduce `d3-focus-label` or rank-driven opacity in Network mode.
- Suggested next command: `curl -fsS http://localhost:13000/api/v1/system/readiness`
