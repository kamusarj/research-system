# US-GRAPH-BOARD-DRILLDOWN Open Node Lists from System Boards

## Status

implemented

## Lane

normal

## Product Contract

The main hierarchy is board-first. Its initial state shows the Business AI Agents system and the
collapsed top-level system boards only. Each board represents one canonical pillar and advertises
how many direct nodes it contains without rendering those nodes yet.

A single click anywhere on a board opens that board and renders its direct node list to the right.
The root breadcrumb returns to the collapsed board overview. Node selection and the relationship
view remain available, and opening a board never changes canonical graph data.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/graph-horizontal-hierarchy.md`

## Acceptance Criteria

- Initial hierarchy renders the root plus the eleven collapsed `SystemPillar` boards and no
  deeper concept nodes.
- A board is visually distinct from a normal node and displays its direct child count plus an
  explicit click-to-open affordance.
- A single click on the board card loads only that board's direct children; the tiny output port is
  not the only way to open it.
- Opening a board retains the root → board breadcrumb and excludes sibling boards from the opened
  node-list view.
- Clicking the root breadcrumb restores the collapsed board overview.
- Relationship mode, selection, filters, zoom and graph governance remain unchanged.
- Unit and cross-viewport browser proof cover the board overview and single-click drilldown.

## Design Notes

- Commands: no new operator command.
- Queries: overview uses hierarchy root at depth 1; an opened board uses that board as root at depth
  1 with a bounded limit large enough for the direct node list.
- API: unchanged.
- Tables: unchanged.
- Domain rules: `SystemPillar` is presented as a board; all other ontology records remain nodes.
- UI surfaces: `/graph`, D3 hierarchy cards, i18n copy and hierarchy E2E.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Page requests depth 1 and exposes board-open state; renderer helper classifies board nodes. |
| Integration | Existing hierarchy API directional traversal remains green. |
| E2E | Single-click board opens direct nodes on desktop/tablet/mobile; breadcrumb restores boards. |
| Platform | Rebuilt frontend serves the live board interaction without console/API errors. |
| Release | Frontend lint, typecheck, tests and production build. |

## Harness Delta

Intake #16 and human correction intervention #2 replace the previous port/focus interaction
interpretation. No architecture decision is needed because the accepted ontology and graph API are
unchanged.

## Evidence

- Initial live hierarchy renders 12 cards: one system root plus eleven visually distinct collapsed
  boards. Each board displays its direct-node count and localized open affordance.
- A single click on the `Data, Knowledge & Memory` board opens 33 direct nodes plus the board/root
  context. The direct nodes wrap into three readable display columns; the opened view excludes all
  sibling boards and retains the `Business AI Agents / Data, Knowledge & Memory` breadcrumb.
- Frontend ESLint and TypeScript pass; all 32 Vitest tests pass, including board classification,
  direct-child query state and large-board multi-column layout.
- The 15-route Next.js production build passes.
- Fifteen Playwright cases pass across desktop/tablet/mobile for board drilldown, all workspace
  hydration, visual tokens, source interaction and page overflow. The focused board spec alone
  passes three viewports.
- The rebuilt frontend is live at `http://localhost:13000/graph`. Runtime health/readiness pass at
  45 canonical nodes / 32 edges, and the real browser check reports no console/page errors.
