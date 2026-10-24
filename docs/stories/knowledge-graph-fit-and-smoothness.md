# US-KNOWLEDGE-GRAPH-FIT-SMOOTH Fit and smooth the Knowledge Graph workspace

## Status

implemented

## Lane

normal

## Product Contract

The explicit Fit action must contain every rendered node inside the visible graph canvas on
desktop, tablet and mobile. The default hierarchy opening may remain at a readable panning scale,
but Fit must provide an honest whole-graph overview. The displayed zoom percentage must match the
actual D3 transform after buttons, wheel/pan, layout changes, data changes and resize.

Pointer movement over Hierarchy must update only the hovered card and its pre-indexed incident
edges. It must not create D3 transitions or rescan/restyle every graph element. Resize work must be
coalesced and skipped when the canvas dimensions did not materially change.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-gitnexus-explorer.md`
- `docs/stories/knowledge-graph-hover-paint-performance.md`

## Acceptance Criteria

- Expanding the real 91-node hierarchy and pressing Fit leaves zero nodes outside the canvas at
  1440×900, 1024×768 and 390×844.
- The zoom badge matches the actual SVG transform after toolbar Fit and canvas zoom controls.
- Hierarchy hover/focus has zero D3 transition owners and updates only the pointed node plus its
  indexed incident edges.
- ResizeObserver work is animation-frame coalesced and ignores unchanged dimensions.
- Network selection/hover, progressive hierarchy leaves, Orbit, inspector and graph semantics remain
  unchanged.
- There is no page-level horizontal overflow or new browser error at the three target viewports.

## Design Notes

- API, database, graph query bounds and canonical data remain unchanged.
- Initial large-hierarchy opening remains readable; explicit Fit uses the complete mathematical fit.
- D3 reports zoom changes through one bounded callback so React does not display stale state.
- Existing adjacency/incident-edge indexes are reused for local hierarchy hover.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Full-fit scale and indexed hover projection helpers. |
| Integration | Canvas reports current zoom and coalesces meaningful resizes. |
| E2E | Expanded hierarchy Fit, zoom accuracy and local hover across three viewports. |
| Platform | Real 429-node runtime, clean console, no overflow, responsive fit counts. |
| Release | Focused ESLint/Vitest/Playwright; full checks where unrelated baseline permits. |

## Harness Delta

Intake #74 records the owner-requested refinement. No architecture decision is required.

## Evidence

- Baseline real runtime after expanding to 91 hierarchy nodes and pressing Fit:
  - desktop: 64 nodes outside canvas; transform scale `0.42`, badge `77%`;
  - tablet: 63 outside; scale `0.42`, badge `71%`;
  - mobile: 64 outside; scale `0.42`, badge `41%`.
- Baseline hierarchy hover code performed full node/edge selections and created 100 ms transitions.
- Final real runtime after expanding the same 91-node hierarchy and pressing Fit:
  - desktop: zero nodes outside; transform/badge `13%`; no page overflow or browser errors;
  - tablet: zero outside; transform/badge `14%`; no page overflow or browser errors;
  - mobile: zero outside; transform/badge `13%`; no page overflow or browser errors.
- Fifty enter/leave cycles with forced-style reads averaged `0.387 ms`, `0.376 ms` and `0.380 ms`
  per event on desktop, tablet and mobile respectively, with zero D3 transition owners.
- Full frontend ESLint passes; all 31 Vitest files / 141 tests pass; responsive hierarchy
  Playwright passes `3/3`.
- Harness story completion passed; standard trace #76 records the implementation and proof.
- Full TypeScript validation remains blocked by the pre-existing unrelated
  `components/document-ai-editor.test.tsx` fixture missing required `DocumentWorkspace.summary`.
