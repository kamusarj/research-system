# US-KNOWLEDGE-GRAPH-GITNEXUS-EXPLORER GitNexus-Inspired Graph Studio

## Status

implemented

## Lane

normal

## Product Contract

The research graph should feel like a focused graph studio rather than a report with a diagram
inside it. It adopts the useful interaction grammar of GitNexus—dark full-canvas exploration,
force/tree/circles-style layout choices, visual communities, floating controls, a bottom status
line and contextual inspection—while retaining this product's research ontology, bilingual copy,
approved-only data and governed mutation flow.

Hierarchy remains a board/card view, but dense branches progressively disclose leaf children.
Parents with many direct leaf nodes show a small representative preview plus an explicit hidden
count; expanding the parent reveals the complete local branch without inventing or deleting
knowledge. The same board view also receives the accepted non-hierarchy relationships whose
endpoints are visible, styled separately from parent/child edges and emphasized contextually so the
structure remains readable.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-visual-redesign.md`
- `docs/decisions/0040-document-knowledge-graph-and-system-map.md`

## Primary Reference

- Official GitNexus repository and current web UI source:
  `https://github.com/abhigyanpatwari/GitNexus`
- Relevant reference implementation files: `gitnexus-web/src/components/GraphCanvas.tsx`,
  `gitnexus-web/src/hooks/useSigma.ts`, `gitnexus-web/src/lib/graph-adapter.ts` and
  `gitnexus-web/src/App.tsx`.

## Acceptance Criteria

- `/graph` presents one dominant dark graph studio with compact chrome, floating search/actions,
  contextual inspector and a useful status bar; it remains part of the existing app shell.
- Users can switch between Network, Hierarchy and Orbit layouts. Network clusters by research node
  type, Hierarchy uses board/cards, and Orbit provides a deterministic concentric overview.
- Dense hierarchy parents preview at most a bounded number of direct leaf children and expose the
  hidden count. Expanding/collapsing occurs locally and preserves all canonical nodes.
- Hierarchy loads accepted relationship edges as a secondary overlay. Parent/child edges and
  semantic relationship edges are visually distinct, selectable and included in the inspector.
- Labels use semantic zoom and neighborhood focus. Type communities, node colors and edge colors
  remain legible against the dark surface.
- Existing graph search, filters, reset, fit, re-layout, node/edge details, evidence, separate
  `/graph/system` route, API contract and governance behavior remain intact.
- Desktop, tablet and mobile controls remain reachable with no page-level horizontal overflow.

## Design Notes

- Commands: no new operator command.
- Queries: keep the existing bounded 1,000-node hierarchy and relationship queries. Hierarchy uses
  the relationship result only as a read-only overlay filtered to currently visible endpoints.
- API: unchanged.
- Tables: unchanged.
- Domain rules: PostgreSQL remains canonical. Leaf collapsing and cross-edge visibility are browser
  presentation state; neither changes approval, hierarchy placement or stored relationships.
- UI surfaces: `/graph`, graph toolbar/canvas/renderer, graph presentation helpers, bilingual copy,
  focused unit tests and responsive graph E2E.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Dense-leaf projection, cross-edge merge, layout switching and renderer helper behavior. |
| Integration | Page keeps bounded synchronized hierarchy/relationship queries and selection details. |
| E2E | Network/Hierarchy/Orbit, leaf expand/collapse, semantic edge selection and responsive overflow. |
| Platform | Rebuilt frontend on `13000`, healthy direct/proxied API and clean live graph console. |
| Release | Frontend ESLint, TypeScript, Vitest and production build. |

## Harness Delta

Intake #63 records this owner refinement. No durable architecture decision is required because the
API, canonical data ownership, accepted graph semantics and governance boundaries do not change.

## Evidence

- Baseline before this refinement: `/tmp/business-ai-graph-pre-gitnexus.png`.
- Final live captures: `/tmp/business-ai-gitnexus-hierarchy-collapsed.png`,
  `/tmp/business-ai-gitnexus-hierarchy-expanded.png`,
  `/tmp/business-ai-gitnexus-network-final-check.png`, and
  `/tmp/business-ai-gitnexus-orbit.png`.
- Live hierarchy projection showed 27 cards, 16 visible semantic cross-links and 64 hidden direct
  leaf nodes; expanding the dense source branch showed 91 cards and 80 semantic links.
- `npm run lint`, `npm run typecheck`, all 134 Vitest tests and `npm run build` passed.
- `E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/graph-hierarchy.spec.ts`
  passed on desktop Chrome, tablet Chrome and mobile Chrome (3/3).
- The rebuilt runtime serves `/graph` on port `13000`; direct API remains on port `18000`.
- Harness trace #64 meets the normal-lane standard tier (2/3).
