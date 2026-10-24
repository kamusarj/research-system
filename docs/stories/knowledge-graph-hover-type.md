# US-KNOWLEDGE-GRAPH-HOVER-TYPE Explicit Type In Network Hover Badge

## Status

implemented

## Lane

normal

## Product Contract

Network nodes remain unlabeled in the resting overview. Hovering or keyboard-focusing a node
reveals one compact badge containing both its explicit human-readable type and its name, so users
never have to infer type from color alone.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-hover-labels.md`

## Acceptance Criteria

- Every Network type/name badge is invisible at rest, regardless of node rank or selection.
- Mouse hover or keyboard focus reveals exactly one badge with the node type above its name.
- The type uses the existing human-readable type formatter and the node's semantic color.
- Leaving/blurring restores zero visible Network type and name labels.
- Hierarchy cards and Orbit semantic labels retain their existing rendering.
- Faint dashed overview edges and indexed direct-edge reveal remain unchanged and transition-free.
- Desktop, tablet and mobile remain usable and overflow-free.

## Design Notes

- Commands: unchanged.
- Queries: unchanged.
- API: unchanged.
- Tables: unchanged.
- Domain rules: node identity, type, importance and relationships are unchanged.
- UI surfaces: Network node hover/focus badge only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Existing graph projection, renderer and compact-glyph tests remain green. |
| Integration | Network rendering emits explicit type text while the resting opacity rule hides the complete badge. |
| E2E | Zero type/name labels at rest, one matching type/name badge on hover, then zero after leave/click across three viewports. |
| Platform | Rebuilt real runtime visually and programmatically proves the same behavior. |
| Release | ESLint, TypeScript, all Vitest tests and production build pass. |

## Harness Delta

Intake #69 and intervention #24 record the owner's clarification of the hover-label contract. No
durable architecture decision is required.

## Evidence

- Network rendering adds a dedicated `.d3-node-type-label` only in relationship mode. It uses the
  existing human-readable type formatter, semantic node color and a two-tier white badge above the
  existing node name; Orbit and Hierarchy markup remain unchanged.
- The resting-label reset, click-focus reset, hover reveal, pointer-event and transition-free CSS
  rules cover the type, name and backdrop as one badge.
- Responsive Chrome E2E proves visible type/name counts `0/0 → 1/1 → 0/0`, matching `CONCEPT` for
  the hovered fixture, and still `0/0` after click selection across desktop, tablet and mobile.
- ESLint, TypeScript, all 136 Vitest tests and the production build pass.
- Live Chrome on the rebuilt 429-node / 370-edge runtime reports zero resting type/name labels,
  exactly one `COLLECTOR SOURCE` / `OpenAI News` badge on hover, 68 revealed direct edges, retained
  `0.08` / `3px, 7px` overview edges and zero browser errors.
