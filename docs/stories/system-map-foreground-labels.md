# US-SYSTEM-MAP-FOREGROUND-LABELS Keep System map text above cards

## Status

implemented

## Lane

normal

## Product Contract

The separate `/graph/system` hierarchy renders its visible type, title, board-action and child-count
text in a dedicated foreground SVG layer. Compound parent cards and any other node card may not
paint over that text. Card geometry, progressive folding, child containment, selection, inspector
and pointer/keyboard behavior remain unchanged.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/system-map-progressive-types.md`
- `docs/stories/knowledge-graph-community-label-layer.md`

## Acceptance Criteria

- System map card shapes remain in `.d3-nodes`; their direct visible text is mirrored into the
  existing `.d3-labels` group after nodes.
- Source text inside each interactive card becomes visually hidden to avoid double-painting, while
  the card's accessible node label remains intact.
- Foreground text is pointer-transparent and uses a restrained canvas-colored outline.
- Collapsed 12-card and expanded 45-card real states retain exact compound containment and current
  click/keyboard behavior.
- Desktop, tablet and mobile prove layer order, visible foreground text and zero horizontal overflow.

## Design Notes

- Commands and API: unchanged.
- Tables and domain rules: unchanged.
- UI surface: `/graph/system` hierarchy text only; primary research hierarchy is unchanged.
- The renderer detects the system projection by the presence of both `SystemRoot` and
  `SystemPillar` nodes.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Renderer and system projection suites remain green. |
| Integration | System nodes still pass through the shared renderer and retain accessibility. |
| E2E | Collapsed/expanded/collapsed flow proves foreground layer order and containment. |
| Platform | Live 45-node runtime proves 12 → 45 cards, foreground text and no errors. |
| Release | Focused/full ESLint, Vitest, TypeScript and production build pass. |

## Harness Delta

Intake #79 and owner-correction intervention #28 record this parity follow-up. No architecture
decision or API change is required.

## Evidence

- The shared renderer recognizes only the separate System projection and mirrors every card's
  direct text into `.d3-labels`, after `.d3-nodes`; source text is visually hidden while the card
  group's accessible name remains intact.
- Foreground overlays are `pointer-events: none` and use `paint-order: stroke fill` with a restrained
  2.5px canvas-colored outline.
- Focused verification passed 18 tests plus ESLint, TypeScript and responsive Chrome E2E 3/3.
- Full frontend ESLint and 32 Vitest files / 144 tests passed; the production Next build generated
  all 15 routes and the rebuilt multi-user frontend became healthy.
- Live Chrome at 1920x1080 proved 12 cards / 12 overlays collapsed and 45 cards / 45 overlays after
  expanding Data, Knowledge & Memory, with correct layer order, zero horizontal overflow and zero
  browser console/page errors.
- Harness story completion passed and standard trace #81 records the execution proof.
