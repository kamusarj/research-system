# US-KNOWLEDGE-GRAPH-HOVER-LABELS Uniform Hover-Only Network Labels

## Status

implemented

## Lane

normal

## Product Contract

Network nodes follow one consistent naming rule: no node label is visible in the resting overview.
Hovering or keyboard-focusing a node reveals only that node's label. Click selection may isolate a
neighborhood but must not expose a batch of labels. Connections remain faint/dashed at rest and
reveal only the hovered node's direct edges.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-edge-reveal.md`

## Acceptance Criteria

- Every Network label and backdrop has zero visible opacity at rest, regardless of node rank.
- Mouse hover or keyboard focus reveals exactly one node label and its backdrop.
- Leaving/blurring restores zero visible Network labels.
- Click selection keeps all labels hidden unless a node is also hovered/focused.
- Faint dashed overview edges and indexed direct-edge reveal remain unchanged and transition-free.
- Desktop, tablet and mobile Network/Hierarchy/Orbit behavior stays usable and overflow-free.

## Design Notes

- Commands: unchanged.
- Queries: unchanged.
- API: unchanged.
- Tables: unchanged.
- Domain rules: node identity, importance and relationships are unchanged.
- UI surfaces: Network labels only; Hierarchy card text and Orbit semantic labels remain unchanged.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Existing graph projection and compact-glyph tests remain green. |
| Integration | Network ranking cannot expose overview labels; hover remains a local class update. |
| E2E | Zero/one/zero labels across rest, hover and leave plus zero labels after click on three viewports. |
| Platform | Rebuilt real 429-node runtime visually and programmatically proves the same rule. |
| Release | ESLint, TypeScript, all Vitest tests and production build pass. |

## Harness Delta

Intake #68 and intervention #23 record the owner's correction to the retained semantic-zoom labels.
No durable architecture decision is required.

## Evidence

- `updateRelationshipLabels()` now assigns opacity zero to every Network label/backdrop, independent
  of importance, degree, zoom or the Labels toolbar state. Orbit keeps its bounded semantic labels.
- Click focus no longer adds `d3-focus-label` to the selected node or ranked neighbors. The existing
  local `d3-node-hovered` class reveals exactly one label/backdrop for mouse and keyboard users.
- Responsive Chrome E2E proves visible-label counts `0 → 1 → 0` for rest/hover/leave and still `0`
  after click selection across desktop, tablet and mobile; faint dashed/revealed edge assertions pass.
- ESLint, TypeScript, all 136 Vitest tests and the production build pass.
- Live Chrome on the rebuilt 429-node / 370-edge runtime reports zero resting labels, one hovered
  label, zero selected-away labels, `0.08` / `3px, 7px` overview edges, 68 revealed incident edges
  for the highest-degree node and zero browser errors.
