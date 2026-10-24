# Knowledge Graph fit and smoothness

## Context

- User request: fit the Knowledge Graph to the screen, improve observability and fix performance
  defects so interaction runs smoothly.
- Agent: Codex
- Date/time: 2026-08-14 09:37 +07

## Work Done

- Files changed:
  - `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`
  - `apps/web/components/knowledge-graph/d3-graph-canvas.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/lib/knowledge-graph/d3-graph-renderer.test.ts`
  - `apps/web/e2e/graph-hierarchy.spec.ts`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `docs/stories/knowledge-graph-fit-and-smoothness.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - Explicit `Fit view` computes an unclamped full-bounds transform with viewport-safe insets.
  - The renderer reports every D3 zoom transform to the React zoom badge.
  - ResizeObserver updates are animation-frame coalesced and unchanged dimensions are skipped.
  - Hierarchy hover directly updates the pointed card and pre-indexed incident edges without global
    D3 selections or transitions.
  - Removed unused hierarchy SVG filters and aligned the zoom extent with small whole-graph scales.
- Commands run:
  - `scripts/bootstrap-harness.sh`
  - `scripts/bin/harness-cli query matrix --active --summary`
  - Harness intake/story add and update commands for intake #74 / story
    `US-KNOWLEDGE-GRAPH-FIT-SMOOTH`
  - `npm run lint`
  - `npm test -- --run`
  - `npm run typecheck`
  - `E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/graph-hierarchy.spec.ts`
  - Real Chrome audits at 1440×900, 1024×768 and 390×844 against the live runtime
  - `scripts/bin/harness-cli story complete US-KNOWLEDGE-GRAPH-FIT-SMOOTH`
  - Standard Harness trace #76

## Reasoning / Decisions

- Decision: keep the initial progressive hierarchy at its readable pan/zoom scale, but make the
  explicit Fit action a mathematically complete overview even below the former `0.42` scale floor.
- Reason: a Fit action that left 63–64 of 91 rendered cards outside the canvas was misleading.
- Decision: retain global focus work for intentional selection while making pointer hover local.
- Reason: hover is high-frequency; selection is deliberate and preserves the existing exploration
  semantics.
- Alternatives considered: shrinking the initial hierarchy automatically was rejected because it
  would make ordinary reading harder; hiding nodes during Fit was rejected because it would not be
  an honest overview.

## Verification

- Tests/checks:
  - Full ESLint: passed.
  - Vitest: 31 files / 141 tests passed.
  - Responsive Playwright: desktop, tablet and mobile passed, 3/3.
  - Harness story verification/completion: passed; standard trace #76 meets the normal-lane tier.
  - Real expanded 91-node hierarchy: zero nodes outside the canvas at all three viewports; zoom
    transform and badge agree at 13%/14%; no page overflow or browser errors.
  - Forced-style hierarchy hover benchmark: approximately 0.38 ms per enter/leave event with zero
    D3 transition owners.
  - `git diff --check` on graph/story files: passed before the final documentation updates.
- Result: requested graph fit and pointer smoothness behavior is implemented and verified.
- Known issue: full `npm run typecheck` fails in the unrelated pre-existing
  `components/document-ai-editor.test.tsx:35` fixture because required `DocumentWorkspace.summary`
  is absent. The graph-focused code, tests and E2E checks pass.

## Next Agent Notes

- Continue from: the runtime already serves the updated frontend at `http://localhost:13000/graph`.
- Watch out for: a complete 91-node Fit view is intentionally a small 13–14% overview; use the
  readable initial hierarchy or zoom in for inspection.
- Suggested next command: `cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/graph-hierarchy.spec.ts`
