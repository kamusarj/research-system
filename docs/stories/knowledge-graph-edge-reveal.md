# US-KNOWLEDGE-GRAPH-EDGE-REVEAL Progressive Network Edge Reveal

## Status

implemented

## Lane

normal

## Product Contract

The Network overview must preserve relationship orientation without drawing hundreds of equally
prominent lines. Connections are faint and dashed at rest. Hovering a node reveals only its direct
connections as clear solid lines, while click selection retains the existing neighborhood focus.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-hover-paint-performance.md`

## Acceptance Criteria

- Resting Network edges are visibly faint and dashed but remain present and selectable.
- Hovering a node reveals exactly its incident edges without toggling corpus-wide focus.
- Leaving the node restores the faint overview; click selection still isolates its neighborhood.
- Hover continues to update only indexed local elements with no D3 transitions or full-edge scan.
- Desktop, tablet and mobile Network/Hierarchy/Orbit behavior remains usable and overflow-free.

## Design Notes

- Commands: unchanged.
- Queries: unchanged.
- API: unchanged.
- Tables: unchanged.
- Domain rules: canonical relationships and edge types are unchanged.
- UI surfaces: Network edge styling and local node-hover reveal only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Existing indexed focus and compact graph tests remain green. |
| Integration | Hover mutates only the incident edge set and click focus remains intact. |
| E2E | Resting/revealed edge styles and counts pass across three viewports. |
| Platform | Rebuilt real 429-node runtime remains healthy and visually readable. |
| Release | ESLint, TypeScript, full Vitest and production build pass. |

## Harness Delta

Intake #67 records this bounded visual refinement. No durable architecture decision is required.

## Evidence

- Network lines use a dedicated `d3-network-edge` overview style at `0.08` opacity with a `3 7`
  dash; Orbit and Hierarchy edge styling remain independent.
- Node hover adds `d3-hover-edge` only to the node's pre-indexed incident edge IDs and removes those
  classes on leave. The revealed lines render at `0.92` opacity as clear solid connections.
- Responsive Chrome E2E verifies rest, reveal, leave restoration, click focus and zero transition
  owners across desktop, tablet and mobile; all 3 cases pass.
- ESLint, TypeScript, all 136 Vitest tests and production build pass.
- On the rebuilt 429-node / 370-edge runtime, the highest-degree node revealed exactly 68 direct
  connections. Fifty enter/leave cycles averaged 0.118 ms (0.8 ms max), with zero long tasks,
  transition owners or browser errors and no leftover revealed classes.
