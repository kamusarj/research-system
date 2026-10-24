# Session Log

## Context

- User request: Make the research knowledge graph look and behave more like GitNexus; make the
  hierarchy/board layout more visual, hide excess child leaves until expand, preserve relationship
  links in the board layout, and run the project for review.
- Agent: Codex
- Date/time: 2026-08-11 10:28 +0700

## Work Done

- Files changed: `apps/web/app/graph/page.tsx`, graph toolbar/canvas/renderer and presentation
  helpers, graph types/themes/styles, bilingual i18n copy, graph page/helper/renderer tests,
  responsive graph E2E, `apps/web/app/globals.css`, the graph intelligence plan, Harness story,
  handoff/task/session logs.
- Behavior changed: `/graph` is now a dark graph studio with Network, Hierarchy and Orbit layouts.
  Network groups nodes visually by type, Orbit arranges a deterministic four-ring overview, and
  Hierarchy renders parent/child cards plus distinct accepted semantic cross-links. Dense parents
  preview four direct leaves and expose an explicit hidden count; local expand restores all leaves
  without mutating canonical graph data. Explorer and toolbar layouts no longer block graph actions
  on tablet or mobile.
- Commands run: Harness bootstrap/intake/story/query commands; official GitNexus source inspection;
  frontend ESLint, TypeScript, Vitest, Next production build; Playwright graph E2E on desktop,
  tablet and mobile; Docker frontend rebuild/recreate; direct/proxied health and runtime HTTP/log
  checks.

## Reasoning / Decisions

- Decision: Treat Network and Orbit as visual layouts over relationship semantics, while Hierarchy
  retains its parent/child query plus a read-only semantic overlay filtered to visible endpoints.
- Reason: This preserves canonical API/data ownership while making the board view explain both
  structure and real relationships.
- Decision: Collapse only dense direct leaf groups, retaining a deterministic four-node preview.
- Reason: Users keep context and an honest count while avoiding unreadable shallow forests.
- Alternatives considered: hiding whole branches or persisting collapse state in the backend; both
  would obscure structure or incorrectly turn presentation state into canonical data.

## Verification

- Tests/checks: `npm run lint`; `npm run typecheck`; `npm run test` (31 files / 134 tests);
  `npm run build`; focused Harness verifier (32 tests plus build); Playwright graph flow on desktop,
  tablet and mobile (3/3); Docker Compose status; direct/proxied `/api/v1/health`; `/graph` HTTP 200;
  recent frontend/API logs.
- Result: All requested functionality and automated checks pass. Runtime is available at
  `http://localhost:13000/graph`, with API at `http://localhost:18000`. Direct and proxied
  `/api/v1/system/readiness` report `ready` with a valid 45-node / 32-edge canonical system graph.
  Harness trace #64 meets the normal-lane standard tier (2/3).

## Known Issues

- 338 approved research nodes still have no parent/child placement and are intentionally reported
  as unplaced in Hierarchy. Curating those source relationships is separate from graph rendering.
- The default host API port 8000 remains occupied by the unrelated `smart_exam_backend`; this stack
  continues to use the documented `18000`/`13000` override.

## Next Agent Notes

- Continue from: owner visual review at `http://localhost:13000/graph`.
- Watch out for: preserve the presentation-only leaf collapse and read-only relationship overlay;
  do not write those states into canonical graph records.
- Suggested next command: `API_PORT=18000 FRONTEND_PORT=13000 docker compose ps`.
