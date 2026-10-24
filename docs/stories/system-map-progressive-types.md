# US-SYSTEM-MAP-PROGRESSIVE-TYPES Progressive System Boards With Explicit Types

## Status

implemented

## Lane

normal

## Product Contract

The separate Business AI Agents system map starts as a readable hierarchy of the system root and
collapsed top-level pillars. Every card names its actual human-readable node type. Expanding one
pillar reveals only its direct children inside that same compound board; collapsing it removes those
children from the visible projection without changing canonical graph data.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-hover-type.md`

## Acceptance Criteria

- The initial system-map canvas contains only the `SystemRoot` and top-level `SystemPillar` nodes.
- A card header displays the actual formatted type, including `SYSTEM PILLAR`, never generic `BOARD`.
- Clicking or keyboard-opening a non-empty pillar reveals only that pillar's direct children inside
  its expanded compound boundary while other pillars remain visible and collapsed.
- Activating the expanded pillar again collapses it and restores the initial projection.
- Selection and the inspector continue to use the complete canonical system graph.
- No system nodes or edges are mutated, deleted or reclassified by folding.
- Desktop, tablet and mobile remain usable and overflow-free.

## Design Notes

- Commands: unchanged.
- Queries: unchanged; `/api/v1/graph/system?limit=1000` remains the source projection.
- API: unchanged.
- Tables: unchanged.
- Domain rules: canonical type, hierarchy and approval data remain unchanged.
- UI surfaces: `/graph/system` visible projection and shared hierarchy type header.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Pure system-map projection proves root/pillar initial state and one-board direct-child expansion. |
| Integration | System page passes projected nodes to the renderer while inspector relationships use full data. |
| E2E | Explicit `SYSTEM ROOT`/`SYSTEM PILLAR`, collapse/expand/collapse counts and compound containment pass on three viewports. |
| Platform | Rebuilt 45-node runtime starts with 12 visible cards and expands the 33-child pillar to 45 cards. |
| Release | ESLint, TypeScript, all Vitest tests and production build pass. |

## Harness Delta

Intake #70 and intervention #25 record the owner's request for system-map parity. No architecture
decision is required because this implements the folding contract already accepted in the product plan.

## Evidence

- `buildSystemMapPresentation()` keeps the complete API graph immutable while projecting only the
  system root, top-level pillars and the direct children of the one opened pillar. Unit tests prove
  initial and expanded node/edge sets plus `expanded_group` isolation.
- `/graph/system` owns only the opened-pillar id. The canvas receives the folded projection while
  selection, relationship lookup, child browsing and the inspector continue to read the full graph.
- Shared hierarchy cards now render the actual formatted node type instead of substituting the
  visual role `BOARD`; the inspector also formats PascalCase types as readable words.
- Responsive Chrome E2E passes 3/3 and proves `SYSTEM ROOT`, `SYSTEM PILLAR`, zero generic `BOARD`
  headers, `2 → 3 → 2` mock folding, direct-child containment and readable inspector type.
- All 138 frontend tests, ESLint, TypeScript and the production build pass.
- Live Chrome on the rebuilt 45-node / 44-edge system graph reports `12 → 45 → 12` visible nodes;
  the expanded pillar contains all 33 direct children, the inspector says `System Pillar`, and no
  browser error is emitted.
