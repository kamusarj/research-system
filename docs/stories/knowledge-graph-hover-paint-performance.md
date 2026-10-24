# US-KNOWLEDGE-GRAPH-HOVER-PAINT-PERF Local-Only Network Hover Paint

## Status

implemented

## Lane

normal

## Product Contract

Moving the pointer across the full Network graph must not restyle or repaint the whole SVG corpus.
Hover provides a lightweight local node/label cue only. Neighborhood isolation and corpus dimming
remain available after an intentional click selection, where their one-time paint cost is useful and
expected.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-network-hover-performance.md`

## Acceptance Criteria

- Relationship hover does not toggle the corpus-wide `d3-relationship-focused` state.
- Hover changes only the current node glyph/label or current edge; no adjacency projection,
  full-corpus opacity change or D3 transition occurs.
- Clicking a node still activates neighborhood focus and bounded labels; clearing selection restores
  the overview.
- A forced-style benchmark on the real 429-node graph reports no long tasks or browser errors.
- Desktop, tablet and mobile hierarchy/Network/Orbit behavior remains usable and overflow-free.

## Design Notes

- Commands: unchanged.
- Queries: unchanged.
- API: unchanged.
- Tables: unchanged.
- Domain rules: unchanged.
- UI surfaces: relationship hover/selection routing, focus CSS and browser performance proof.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Focus projection and compact glyph tests remain green. |
| Integration | Hover stays local; click selection still applies indexed neighborhood focus. |
| E2E | Explicit hover-versus-click focus contract passes across three viewports. |
| Platform | Forced-style real-graph benchmark has zero long tasks/errors; runtime rebuilt healthy. |
| Release | ESLint, TypeScript, all Vitest tests and production build pass. |

## Harness Delta

Intake #66 and intervention #22 record the owner's correction to the prior JavaScript-only proof.
No durable architecture decision is required.

## Evidence

- `D3GraphRenderer` now keeps relationship hover local, applies indexed corpus focus only for click
  selection, settles the force layout before display, and performs no delayed fit animation.
- Relationship glyphs and label backdrops no longer use SVG filters; hover handlers no longer mutate
  an inherited cursor style on the graph container.
- `graph-hierarchy.spec.ts` asserts the hover/click state split and zero D3 transition owners across
  desktop, tablet and mobile Chrome; all three cases pass in about 8 seconds total.
- ESLint, TypeScript, all 136 Vitest tests, the focused 34-test Harness verifier and production build
  pass. The rebuilt runtime is ready at frontend `13000` / API `18000`.
- Live Chrome on the real 429-node / 370-edge Network measured forced style at 0.068 ms average /
  0.4 ms maximum and hover frames at 16.357 ms average / 16.8 ms maximum. It reported zero
  post-switch long tasks, transition owners and browser errors, no corpus focus during hover, and
  stable node positions. Intervention #22 and trace #67 retain the correction/proof trail.
