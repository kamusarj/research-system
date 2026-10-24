# Session Log

## Context

- User request: Hide Network connections when not hovered, or render them faint/dashed, and reveal
  useful relationships on pointer hover.
- Agent: Codex
- Date/time: 2026-08-11 11:42 +0700

## Work Done

- Files changed:
  - `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`
  - `apps/web/app/globals.css`
  - `apps/web/e2e/graph-hierarchy.spec.ts`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `docs/stories/knowledge-graph-edge-reveal.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - Network overview edges render at 0.08 opacity with a `3 7` dash pattern.
  - Hovering/focusing a node adds a reveal class only to its pre-indexed incident edges; they become
    0.92-opacity solid lines. Leaving the node removes those classes.
  - Click selection retains the existing indexed neighborhood focus and bounded label behavior.
  - Hierarchy structural/semantic edges and Orbit edges retain their previous visual semantics.
- Commands run:
  - `scripts/bootstrap-harness.sh`
  - Harness intake/story/trace commands (intake #67, trace #68)
  - `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`
  - `npm run test:e2e -- e2e/graph-hierarchy.spec.ts`
  - `docker compose build frontend`
  - `FRONTEND_PORT=13000 docker compose up -d --no-deps frontend`
  - Live Playwright/Chrome screenshots and hover-performance proof
  - Runtime `/graph` and readiness checks

## Reasoning / Decisions

- Decision: Keep edges faint/dashed instead of fully removing them.
- Reason: The overview retains enough orientation to show that clusters are connected while node
  shapes and communities remain the dominant visual layer.
- Decision: Reveal only incident edges through the existing index.
- Reason: It provides a precise answer to “what is this node connected to?” without scanning or
  repainting the complete 370-edge corpus on every pointer movement.
- Alternatives considered: Fully hidden edges were visually cleaner but removed all overview
  orientation; whole-network hover focus would reintroduce the paint cost fixed in intake #66.

## Verification

- Tests/checks:
  - ESLint and TypeScript pass.
  - Vitest: 31 files / 136 tests pass.
  - Focused Harness verifier: 4 files / 34 tests plus production build pass.
  - Playwright desktop/tablet/mobile: 3/3 pass, covering rest, reveal, leave restoration, click focus
    and zero D3 transition owners.
  - Live 429-node / 370-edge graph: overview opacity `0.08`, dash `3px, 7px`; highest-degree node
    reveals exactly 68 edges at opacity `0.92` and solid dash; 50 hover cycles average 0.118 ms /
    max 0.8 ms with zero long tasks, transitions, errors and leftover reveal classes.
  - `/graph` and proxied `/api/v1/system/readiness` return HTTP 200; readiness is valid.
- Result: Passed. Rebuilt frontend is live at `http://localhost:13000/graph`.

## Known Issues

- Running `next build` while the host `next dev` server is active can replace shared `.next` chunks.
  One E2E rerun exposed this; validation passed after stopping/restarting dev and serializing build.
- The unrelated `smart_exam_backend` still owns host port 8000; this project keeps API port 18000.

## Next Agent Notes

- Continue from: Runtime is healthy and ready for owner visual review.
- Watch out for: Do not replace indexed `d3-hover-edge` updates with a full edge selection on hover.
- Suggested next command: `curl -fsS http://localhost:13000/api/v1/system/readiness`
