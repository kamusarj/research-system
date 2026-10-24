# Knowledge Graph text cleanup

## Context

- User request: remove redundant UI text from the Knowledge Graph to reduce visual clutter, and
  change text only.
- Agent: Codex
- Date/time: 2026-08-14 11:22 +07
- Harness intake: #77, tiny change request with `existing_behavior` risk.
- Harness trace: #79, standard tier (exceeds the tiny-lane minimum).

## Files Changed

- `apps/web/app/graph/page.tsx`
- `apps/web/components/knowledge-graph/d3-graph-canvas.tsx`
- `apps/web/lib/i18n.tsx`
- `apps/web/app/globals.css`
- `apps/web/app/graph/page.test.tsx`
- `apps/web/e2e/graph-hierarchy.spec.ts`
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`

## Decisions Made

- Removed only repeated explanatory prose: the page eyebrow and intro, hierarchy banners, canvas
  guide card and persistent mouse interaction sentence.
- Preserved every functional control and label, graph node text, title, compact metrics,
  loading/empty/error states, non-PostgreSQL notice and truncation/safety warning.
- Kept data visibility honest by moving hidden-leaf and unplaced-node counts into the existing
  compact bottom status line instead of removing those facts.
- Scoped the change to primary `/graph`; the separate system map and other pages are unchanged.

## Commands and Tests Run

- `scripts/bootstrap-harness.sh`
- `scripts/bin/harness-cli query matrix --active --summary`
- `scripts/bin/harness-cli intake ...` → intake #77
- Focused ESLint, 26 focused Vitest tests and TypeScript check: passed.
- `npm run build`: passed, 15 routes.
- Rebuilt/recreated the multi-user frontend and waited for health: passed.
- First responsive Playwright run: failed only because one old assertion still expected the
  intentionally removed Network guide title.
- Updated that assertion to verify the guide stays absent and compact cluster status remains.
- Responsive Playwright rerun: desktop/tablet/mobile 3/3 passed.
- Full `npm run lint` and Vitest: 32 files / 144 tests passed.
- Live Chrome 1920×1080 geometry, UI and browser-error audit: passed.
- `git diff --check` on the product change: passed.

## Verification Result

- Live primary graph contains zero `.graph-canvas-guide` and zero `.graph-structure-note`
  elements.
- Compact status reads `27 nodes · 15 hierarchy links · 16 semantic links · 64 hidden leaves ·
  338 unplaced` for the current corpus.
- Studio remains `97.0%` of the 1920px viewport, with zero horizontal overflow and zero console or
  page errors.
- Visual proof: `/tmp/business-ai-graph-clean-ui-1920x1080.png`.
- Runtime: frontend healthy on `13000`; API health remains on `18000`.

## Known Issues

- None introduced by this text-only cleanup.

## Next Best Action

- Have the owner review `http://localhost:13000/graph`; make further removals only when a specific
  remaining label is identified, so functional discoverability is not reduced accidentally.
