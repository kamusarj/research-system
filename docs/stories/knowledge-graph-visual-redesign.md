# US-KNOWLEDGE-GRAPH-VISUAL-REDESIGN Readable Progressive Graph Explorer

## Status

implemented

## Lane

normal

## Product Contract

The research knowledge graph must help a reader understand structure instead of shrinking the
complete corpus into an unreadable overview. Hierarchy and relationship remain synchronized views
of the same approved corpus, but each view uses presentation suited to its job: hierarchy presents
connected parent/child branches and explicitly accounts for unplaced knowledge; relationship uses
semantic zoom, visual priority and neighborhood emphasis to keep the full network explorable.

The canvas is the primary workspace. Filters, legend and inspection remain available without
permanently consuming most of the graph width. Search, keyboard selection, fit, reset, node detail,
neighbor expansion and the separate Business AI Agents system map remain intact.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/decisions/0040-document-knowledge-graph-and-system-map.md`
- `docs/stories/graph-horizontal-hierarchy.md`
- `docs/stories/graph-compound-folding-boards.md`

## Primary Visual References

- Sigma.js graph data/appearance: `https://www.sigmajs.org/docs/advanced/data/`
- Cytoscape.js layouts: `https://js.cytoscape.org/#layouts`
- React Flow sub-flow grouping: `https://reactflow.dev/learn/layouting/sub-flows`
- yFiles folding: `https://docs.yworks.com/yfiles-html/dguide/folding/`

## Acceptance Criteria

- The live 429-node corpus no longer renders hierarchy as an almost invisible line or relationship
  as a wall of equally prominent labels.
- Hierarchy draws only nodes participating in the visible parent/child structure and reports the
  number of approved nodes not yet placed in that structure; search/focused branch queries remain
  able to surface a specific node.
- Relationship overview retains the complete bounded corpus, sizes nodes by importance, limits
  overview labels to meaningful hubs, and emphasizes the selected/hovered node neighborhood while
  muting unrelated nodes and edges.
- The canvas receives the dominant width. Filters/legend use a compact explorer rail and the node
  inspector opens as a canvas-side sheet instead of reserving an empty column.
- The graph supplies an on-canvas view guide and clear controls for fit, re-layout, reset and zoom.
- Desktop, tablet and mobile have no page-level horizontal overflow; controls remain reachable and
  the canvas remains usable.
- Existing API, graph data, system-map separation, selection accessibility and governance behavior
  do not change.

## Design Notes

- Commands: no new operator command.
- Queries: keep the existing bounded 1,000-node API request and focused hierarchy query.
- API: unchanged.
- Tables: unchanged.
- Domain rules: PostgreSQL remains canonical; hiding unplaced nodes from the hierarchy canvas is a
  view concern and does not delete, reclassify or publish knowledge.
- UI surfaces: `/graph`, D3 renderer, hierarchy projection helper, graph toolbar/rail/inspector,
  bilingual copy and focused tests.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Projection selection, semantic-label priority, page/view behavior and renderer interaction. |
| Integration | Existing graph page/API mocks and synchronized view behavior remain green. |
| E2E | Live/mocked hierarchy and relationship views at desktop/tablet/mobile with no overflow. |
| Platform | Rebuilt frontend on `13000`, direct/proxied health and clean graph page console. |
| Release | Frontend ESLint, TypeScript, Vitest and production build. |

## Harness Delta

Intake #62 records the owner correction. No architecture decision is needed because the graph
contract and corpus remain unchanged; this story replaces only the ineffective all-elements-equal
presentation with progressive disclosure and semantic zoom.

## Evidence

- Baseline live screenshots: `/tmp/business-ai-graph-before.png` and
  `/tmp/business-ai-graph-relationship-before.png` show the hierarchy collapsed to an unreadable
  line and the relationship hairball before implementation.
- Final live screenshots: `/tmp/business-ai-graph-final-hierarchy-desktop.png`,
  `/tmp/business-ai-graph-final-hierarchy-tablet.png`,
  `/tmp/business-ai-graph-final-hierarchy-mobile.png` and
  `/tmp/business-ai-graph-final-relationship-focus-desktop.png` show the branch atlas, responsive
  canvas and selected-neighborhood focus against the real corpus.
- Frontend ESLint, TypeScript, all 31 Vitest files / 130 tests and the 15-route production build
  pass. The story verification command passes its focused 28 tests and build.
- Playwright passes 6/6 hierarchy/system-map scenarios across desktop, tablet and mobile. A
  separate live-data audit measured no document overflow and no console/page errors at 1440, 1024
  and 390 px; relationship retains 429 nodes with 26 semantic overview labels, while hierarchy
  shows 91 connected nodes and accounts explicitly for the other 338 as unplaced.
- Rebuilt Compose runtime is live on frontend `13000` and API `18000`; direct/proxied health,
  readiness (`ready`, valid 45-node / 32-edge canonical system graph) and `/graph` HTTP 200 pass.
