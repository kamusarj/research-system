# US-GRAPH-COMPOUND-BOARDS Expand Boards as Compound Containers

## Status

implemented

## Lane

normal

## Product Contract

Top-level system pillars are folding compound boards, not ordinary tree nodes. In the collapsed
state, a board is one compact folder-like card with a child count. Expanding the board changes that
same card into a group container and lays its direct child nodes inside the container boundary.

The system root and other collapsed boards remain visible to preserve the user's mental map. Only
one board is expanded at a time. Clicking the expanded group header collapses it again. Folding
changes the visible projection only; it never changes canonical nodes, parent relationships or
review governance.

## Relevant Product Docs and Primary References

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- React Flow sub-flows/group nodes:
  `https://reactflow.dev/learn/layouting/sub-flows`
- Cytoscape.js compound nodes:
  `https://js.cytoscape.org/#compound-nodes`
- yFiles folding concepts:
  `https://docs.yworks.com/yfiles-html/dguide/folding/`
- yFiles collapsible tree interaction:
  `https://live.yworks.com/demos/view/collapse/`

## Acceptance Criteria

- Initial hierarchy shows the system root and eleven collapsed board cards; no child node is visible
  inside a closed board.
- Clicking a collapsed board lazily loads its direct children and expands that same board into a
  bounded visual container.
- Every visible direct child is geometrically inside the expanded board boundary.
- Other boards remain visible and collapsed; expanding a second board collapses the first.
- Clicking the expanded board header or its collapse control removes its children from the view.
- Containment edges from a board to its children are not drawn over the group contents; the
  container boundary conveys membership.
- Node selection, relationship mode, filtering, zoom and governance remain unchanged.
- Desktop/tablet/mobile tests prove collapse, expansion, containment and no page overflow.

## Design Notes

- Commands: no new operator command.
- Queries: the root/board overview remains depth 1; one additional depth-1 board query is enabled
  only for the expanded board and merged into the visible projection.
- API: unchanged.
- Tables: unchanged.
- Domain rules: `SystemPillar` is the group boundary; direct canonical children are compound
  members only in the view model.
- UI surfaces: graph page state, graph mapper, hierarchy layout, D3 renderer and hierarchy E2E.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Overview/expanded query state, graph merge, compound bounds and child containment. |
| Integration | Existing directional hierarchy API remains green. |
| E2E | Collapse/expand and geometric containment on desktop/tablet/mobile. |
| Platform | Rebuilt frontend, live Chrome screenshot and clean console/API logs. |
| Release | Frontend lint, typecheck, tests and production build. |

## Harness Delta

Intake #17 and correction intervention #3 make the web-researched compound/folding pattern
authoritative. This supersedes the external-branch presentation in
`US-GRAPH-BOARD-DRILLDOWN` without changing graph storage or API contracts.

## Evidence

- The hierarchy overview remains one `SystemRoot` plus eleven collapsed `SystemPillar` boards.
- Expanding a board runs one additional direct-child query, merges it with the overview, and marks
  only the selected board as an expanded view-only group.
- The deterministic compound layout computes the group boundary first and proves every child card
  lies inside it; the D3 renderer hides internal containment edges and keeps sibling boards visible.
- TypeScript, all 32 frontend unit tests and the 15-route production build pass.
- The complete Playwright run passes 30 enabled cases across desktop/tablet/mobile with six expected
  auth-only skips. The focused Harness verifier passes all three compound-board viewport cases.
- Live Chrome proof on frontend `13000` shows `Data, Knowledge & Memory` expanded as one bounded
  three-column container containing all 33 direct child nodes. API `18000` and frontend `13000`
  return HTTP 200.
- Harness story completion passed and standard trace #26 records the implementation.
