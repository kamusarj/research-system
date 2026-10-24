# US-KNOWLEDGE-GRAPH-COMMUNITY-LABEL-LAYER Keep Network community labels above nodes

## Status

implemented

## Lane

normal

## Product Contract

Network community headings such as `RESEARCH ITEM · 79` and `TECHNOLOGY · 7` must remain readable
when community halos overlap. Node glyphs may not paint over those headings. Node positions, halo
geometry, hover/focus behavior, layout switching and Hierarchy/Orbit rendering remain unchanged.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-hover-labels.md`
- `docs/stories/knowledge-graph-light-canvas.md`

## Acceptance Criteria

- Network halo circles remain in the background community layer.
- Network community text renders in the existing foreground label layer after edges and nodes.
- Community text uses a restrained canvas-colored outline so it stays legible over an accidental
  node intersection without becoming a new card or blocking pointer input.
- Node labels remain hover/focus-only and all current interaction/performance behavior is preserved.
- Desktop, tablet and mobile browser proof verifies label layer order, readability styling and zero
  horizontal overflow.

## Design Notes

- Commands: unchanged.
- Queries: unchanged.
- API and tables: unchanged.
- Domain rules: graph data, node identity and community membership are unchanged.
- UI surface: Network community headings only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Focus, fit and renderer helpers remain green. |
| Integration | Community halos and headings are rendered by separate ordered SVG groups. |
| E2E | All responsive projects prove headings are after nodes, outlined and pointer-transparent. |
| Platform | Live 429-node Network screenshot and DOM audit show readable headings and no errors. |
| Release | Focused/full ESLint, Vitest, TypeScript and production build pass. |

## Harness Delta

Intake #78 and owner-correction intervention #27 record the screenshot-discovered z-order gap. No
architecture decision is required.

## Evidence

- `renderCommunities()` now owns only background halo circles; `renderLabels()` creates the
  community headings in `.d3-labels`, which is ordered after `.d3-nodes` in the SVG container.
- Community headings use a `3px` canvas-colored stroke with `paint-order: stroke fill` and retain
  `pointer-events: none`.
- Responsive Playwright passes 3/3 and asserts community headings exist, the label group follows
  the node group, outline styling is active, pointer events remain disabled and horizontal overflow
  stays zero.
- Live 1920×1080 Chrome on the real 429-node / 370-edge Network found 10 community headings and
  five real heading/glyph intersections (`Research Item · 79` and `Technology · 70`). All headings
  are foreground-painted and outlined; browser errors and horizontal overflow are both zero.
- Focused ESLint, 7 renderer tests and TypeScript pass. Full ESLint, 32 Vitest files / 144 tests and
  the 15-route production build pass.
- Runtime frontend was rebuilt and is healthy on `13000`; visual proof was inspected at
  `/tmp/business-ai-community-label-layer.png` and then removed as temporary output.
- Harness story completion passed; standard trace #80 records the implementation and live proof.
