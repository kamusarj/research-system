# Session Log

## Context

- User request: Continue with the next implementation step after the Graph Intelligence Phase 1 backend foundation.
- Agent: Codex
- Date/time: 2026-07-18 10:21 +07

## Work Done

- Files changed:
  - `apps/api/app/api/ontology.py`
  - `apps/api/tests/test_ontology.py`
  - `apps/web/app/graph/page.tsx`
  - `apps/web/app/graph/page.test.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/components/knowledge-graph/d3-graph-canvas.tsx`
  - `apps/web/components/knowledge-graph/graph-toolbar.tsx`
  - `apps/web/components/knowledge-graph/node-details-panel.tsx`
  - `apps/web/components/knowledge-graph/node-details-panel.test.tsx`
  - `apps/web/hooks/use-knowledge-graph.ts`
  - `apps/web/hooks/use-ontology-node.ts`
  - `apps/web/lib/i18n.tsx`
  - `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`
  - `apps/web/lib/knowledge-graph/d3-graph-styles.ts`
  - `apps/web/lib/knowledge-graph/graph-api.ts`
  - `apps/web/lib/knowledge-graph/graph-theme.ts`
  - `apps/web/lib/knowledge-graph/hierarchy-layout.ts`
  - `apps/web/lib/knowledge-graph/hierarchy-layout.test.ts`
  - `apps/web/lib/knowledge-graph/ontology-api.ts`
  - `apps/web/lib/knowledge-graph/types.ts`
  - `apps/web/e2e/graph-hierarchy.spec.ts`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - Added approved ontology root and node breadcrumb endpoints.
  - Added a relationship/hierarchy segmented switch while preserving the current inspector selection.
  - Hierarchy mode loads a root and only its one-hop branch, then navigates by breadcrumb, child list or node double-click.
  - Added a stable layered D3 hierarchy force layout without replacing the existing relationship force layout.
  - Added overview, children, evidence and provenance node-detail tabs with safe handling for selections preserved from the other view.
  - Added English/Vietnamese hierarchy and detail-panel labels plus responsive styling.
- Commands run:
  - `uv run --extra dev python -m ruff check app tests`
  - `uv run --extra dev python -m pytest -q tests/test_ontology.py`
  - `uv run --extra dev python -m pytest -q`
  - `npm run lint`
  - `npm run typecheck`
  - `npm test`
  - `npm run build`
  - `E2E_BASE_URL=http://127.0.0.1:13001 npx playwright test e2e/graph-hierarchy.spec.ts`
  - `git diff --check -- ...`

## Reasoning / Decisions

- Decision: resolve ontology roots first, then query `/graph?view=hierarchy&root_node_id=...&depth=1` rather than loading the complete ontology projection.
- Reason: hierarchy navigation must remain bounded as the canonical graph grows.
- Decision: keep one D3 renderer and switch its force configuration between relationship and hierarchy modes.
- Reason: this preserves zoom/selection lifecycle and avoids duplicating canvas event/cleanup logic.
- Decision: preserve a node selected in the other view in the inspector but do not call ontology APIs for an ID absent from the current hierarchy branch.
- Reason: this satisfies selection continuity without causing invalid breadcrumb/children requests.

## Verification

- Tests/checks:
  - Backend Ruff and full Pytest suite.
  - Frontend ESLint, TypeScript, Vitest and production build.
  - Mocked Playwright hierarchy navigation and horizontal-overflow checks at desktop, tablet and mobile viewports.
- Result:
  - 47 backend tests passed with one existing Starlette/httpx deprecation warning.
  - 15 frontend unit tests passed.
  - ESLint, TypeScript and Next.js production build passed.
  - 3/3 hierarchy Playwright projects passed.
  - The first E2E attempt failed because the broad test mock intercepted `/graph/stats`; route precedence was corrected and the final run passed. No application runtime defect remained.

## Next Agent Notes

- Continue from: Phase 3 gold paper fixtures and deterministic paper-fit scoring before upload worker orchestration.
- Watch out for: the workspace contains extensive pre-existing user changes. Do not revert unrelated frontend work. The new hierarchy UI is verified against mocked API data and SQLite/backend tests, but the current Docker stack has not been rebuilt with migration `8c2d4e6f901a`.
- Suggested next command: inspect the accepted paper-fit rubric in sections 9 and 18 of `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`, then add deterministic scoring schemas/service/fixtures before introducing storage writes.
