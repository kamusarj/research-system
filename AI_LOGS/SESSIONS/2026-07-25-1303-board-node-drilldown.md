# Board-first Node Drilldown

## User Request

- Correct the hierarchy interpretation: each system table/board contains a list of nodes, and the
  nodes should appear only after the user clicks that board.

## Files Changed

- Product/story: `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`,
  `docs/stories/graph-board-drilldown.md`.
- Graph page/presentation: `apps/web/app/graph/page.tsx`, `apps/web/app/globals.css`,
  `apps/web/components/knowledge-graph/d3-graph-canvas.tsx`,
  `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`,
  `apps/web/lib/knowledge-graph/hierarchy-layout.ts`, `apps/web/lib/i18n.tsx`.
- Tests: `apps/web/app/graph/page.test.tsx`,
  `apps/web/lib/knowledge-graph/d3-graph-renderer.test.ts`,
  `apps/web/lib/knowledge-graph/hierarchy-layout.test.ts`,
  `apps/web/e2e/graph-hierarchy.spec.ts`.
- Handoff: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, this session log.
- Harness: intake #16, correction intervention #2 and story
  `US-GRAPH-BOARD-DRILLDOWN`.

## Decisions Made

- `SystemPillar` is the UI board boundary; canonical concepts remain nodes.
- Initial hierarchy renders only the root and collapsed boards.
- A single click anywhere on a board opens only its direct children with a limit of 40.
- The root breadcrumb restores the board overview.
- Large direct-node lists wrap into multiple display columns while preserving parent edges.
- No API, database, canonical ontology or graph-approval behavior changed.

## Commands/Tests Run

- Harness bootstrap, intake #16, normal story and human correction intervention #2.
- `npm run lint`
- `npm run typecheck`
- `npm test -- --run`: 32 tests passed.
- `npm run build`: all 15 Next.js routes built.
- `E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/graph-hierarchy.spec.ts --workers=1`:
  three viewport cases passed.
- Focused hierarchy plus workspace browser suite: 15 cases passed across desktop/tablet/mobile.
- Rebuilt/recreated only the frontend service.
- Direct frontend/API health, readiness, Compose status, service-log scan and `git diff --check`.
- Real Chrome screenshots before/after opening the `Data, Knowledge & Memory` board.
- Harness story completion and detailed trace #25; final audit entropy `0/100`.

## Verification Result

- Live initial view contains one root and eleven collapsed boards.
- Each board displays a localized board label, direct-node count and click-to-open affordance.
- One click on `Data, Knowledge & Memory` opens 33 direct nodes in three display columns, retains
  the root/board breadcrumb and excludes sibling boards.
- The real browser recorded no console or page errors.
- Runtime is healthy and ready with a valid 45-node / 32-edge canonical graph.

## Known Issues

- The first combined E2E run reached the final breadcrumb step but used a non-exact role selector
  that also matched the SVG output port. The selector was narrowed to the exact breadcrumb button;
  all three viewports and the broader 15-case rerun pass.
- Boards with zero direct canonical nodes remain visible with count zero by design so the ontology
  frame remains stable and future AI placement has an explicit destination.
- Existing production dependency advisories remain separate maintenance work.

## Next Best Action

1. Linh verifies the board terminology and click behavior at `http://localhost:13000/graph`.
2. Linh reviews the already prepared grounded DeepSeek change set and records the Graph v2 product
   decision.
