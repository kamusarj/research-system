# US-KNOWLEDGE-GRAPH-NETWORK-HOVER-PERF Smooth Network Hover and Smaller Glyphs

## Status

implemented

## Lane

normal

## Product Contract

Hovering nodes in the full Network graph must respond immediately rather than scheduling SVG
transitions and repeated full-graph DOM passes. Neighborhood focus, labels and selection remain
useful, while painted node/control icons become smaller again without reducing the existing 44 px
interaction target.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-light-canvas.md`

## Acceptance Criteria

- Network hover does not allocate a transition for every node and edge.
- Focus updates touch only the previous/current focus node, its neighbors and incident edges; all
  unrelated dimming is handled by one root CSS state.
- Focus labels remain bounded to the focus node and at most 16 ranked neighbors.
- Toolbar, guide, zoom and painted node glyphs are smaller while interaction hit targets remain at
  least 44 px.
- Real 429-node hover benchmark, existing selection behavior and desktop/tablet/mobile graph flow
  pass without overflow or browser errors.

## Design Notes

- Commands: unchanged.
- Queries: unchanged.
- API: unchanged.
- Tables: unchanged.
- Domain rules: graph semantics and canonical data are unchanged.
- UI surfaces: D3 renderer focus path, graph CSS/sizing, unit and browser regression proof.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Focus projection is bounded and deterministic; compact radius values are covered. |
| Integration | Selection/hover focus and label behavior remain compatible with the graph page. |
| E2E | Full graph flow passes on three viewports with compact computed icon bounds. |
| Platform | Real 429-node repeated hover benchmark and rebuilt runtime health pass. |
| Release | ESLint, TypeScript, all Vitest tests and production build pass. |

## Harness Delta

Intake #65 records this owner-reported performance refinement. No durable decision is required.

## Evidence

- Real runtime benchmark on 429 nodes / 370 edges: 100 enter/leave cycles completed in 3.50 ms
  total (0.035 ms average), with zero node/edge D3 transition owners and zero console/page errors.
- Final Network capture: `/tmp/business-ai-network-hover-final.png`.
- Network hover now switches one SVG root class and updates only indexed focus, neighbor, label and
  incident-edge elements. Focus labels remain capped at 16 neighbors.
- Toolbar icons are capped at 9 px, guide icons at 12 px and zoom icons at 10 px. Painted node bases
  are 8–15 px with a 7 px maximum degree bonus; invisible hit targets remain 44 px.
- ESLint, TypeScript, 31 Vitest files / 136 tests and the 15-route production build pass.
- Responsive hierarchy/Network/Orbit Playwright passes desktop, tablet and mobile (3/3), asserting
  compact glyphs, computed focus opacity and zero hover transition owners.
- Harness trace #66 meets the normal-lane standard tier (2/3).
