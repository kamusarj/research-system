# US-KNOWLEDGE-GRAPH-LIGHT-CANVAS Light Graph Canvas and Compact Icons

## Status

implemented

## Lane

normal

## Product Contract

The GitNexus-inspired research graph keeps its Network, Hierarchy and Orbit behavior while using a
clean white workspace that matches the rest of the application. Graph nodes and interface icons are
smaller so the canvas gives relationships more breathing room without reducing click reachability,
legibility or responsive behavior.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-gitnexus-explorer.md`

## Acceptance Criteria

- The graph studio, toolbar, canvas, Explorer, inspector, guide and status bar use a cohesive light
  palette with sufficient contrast.
- Toolbar, guide and zoom icons are visibly smaller while their button hit areas remain usable.
- Network and Orbit node glyphs use a more compact radius; hierarchy cards, progressive leaf
  disclosure and semantic cross-links remain unchanged in behavior.
- Desktop, tablet and mobile graph interactions remain reachable without horizontal overflow.

## Design Notes

- Commands: unchanged.
- Queries: unchanged.
- API: unchanged.
- Tables: unchanged.
- Domain rules: canonical graph data and presentation semantics are unchanged.
- UI surfaces: `/graph` studio CSS, D3 node sizing/colors and responsive graph E2E.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Existing graph presentation/renderer tests remain green. |
| Integration | Graph page layout switching and progressive hierarchy tests remain green. |
| E2E | Light computed surface, compact icons/nodes and full interaction flow across three viewports. |
| Platform | Rebuilt frontend is live on `13000` and graph/API health pass. |
| Release | ESLint, TypeScript, Vitest and production build pass. |

## Harness Delta

Intake #64 records this visual refinement. No durable architecture decision is needed.

## Evidence

- Final live capture: `/tmp/business-ai-graph-light-canvas.png`.
- Browser-computed proof confirms studio `rgb(255, 255, 255)`, canvas
  `rgb(251, 252, 254)` and toolbar icons no larger than 11 px.
- Network/Orbit glyph bases are reduced to 10–18 px with a bounded degree bonus; every glyph keeps
  an invisible minimum 44 px interaction target.
- ESLint, TypeScript, 31 Vitest files / 135 tests and the 15-route production build pass.
- Responsive graph Playwright passes on desktop, tablet and mobile Chrome (3/3), including the full
  hierarchy expand, Network selection and Orbit flow.
- Harness trace #65 meets the normal-lane standard tier (2/3).
