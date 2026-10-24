# Knowledge Graph community label layer fix

## Context

- User request: fix Network text being covered by nodes in screenshot
  `/home/linh/Pictures/Screenshots/Screenshot From 2026-08-14 11-28-19.png`.
- Agent: Codex
- Date/time: 2026-08-14 11:34 +07
- Harness: intake #78, normal story `US-KNOWLEDGE-GRAPH-COMMUNITY-LABEL-LAYER`, owner-correction
  intervention #27 and standard trace #80.

## Files Changed

- `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`
- `apps/web/app/globals.css`
- `apps/web/e2e/graph-hierarchy.spec.ts`
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-community-label-layer.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`

## Decisions Made

- Identified the covered text as Network community type/count headings, not hover-only node labels.
- Kept halo circles in `.d3-communities` behind edges/nodes and moved only heading text into the
  existing `.d3-labels` group after `.d3-nodes`.
- Added a restrained 3px canvas-colored text outline using SVG paint order, rather than adding a
  new card or changing node positions.
- Kept headings pointer-transparent so hover, drag and selection behavior remains unchanged.

## Commands and Tests Run

- Required startup reads, Harness bootstrap, active matrix query and screenshot inspection.
- Harness intake/story/intervention lifecycle and fresh story completion.
- Focused ESLint, 7 renderer Vitest tests and TypeScript: passed.
- Production Next build: passed, 15 routes.
- Rebuilt and recreated the multi-user frontend with health wait: passed.
- Responsive Playwright desktop/tablet/mobile: 3/3 passed, both direct and through story completion.
- Full frontend ESLint and 32 files / 144 Vitest tests: passed.
- Live Chrome 1920×1080 DOM geometry/layer/style/error audit on the real 429-node Network: passed.
- `git diff --check`: passed.

## Verification Result

- The live graph renders 10 community headings after the node group in SVG order.
- The real layout contains five heading/glyph intersections involving `Research Item · 79` and
  `Technology · 70`; those headings now paint in front with `paint-order: stroke`, a 3px outline and
  `pointer-events: none`.
- Horizontal overflow and browser console/page errors are both zero.
- The temporary validation screenshot was inspected and removed from `/tmp` afterward.
- Frontend remains healthy at `http://localhost:13000/graph`; API health is available on `18000`.

## Known Issues

- None introduced by this fix.

## Next Best Action

- Owner refreshes `/graph`, opens Network and confirms the community headings remain readable at
  their preferred zoom level.
