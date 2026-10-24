# US-KNOWLEDGE-GRAPH-FULL-VIEWPORT Use the wide viewport for Knowledge Graph

## Status

implemented

## Lane

normal

## Product Contract

The primary `/graph` route must use nearly all available browser width instead of inheriting the
shared reading-page `1440px` cap. At the owner's 1920×1080 viewport, the Graph Studio must expand
to at least 95% of the viewport width while preserving responsive padding, toolbar reachability,
canvas fit, overlays and zero page-level horizontal overflow. Other application routes retain their
existing readable width.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/knowledge-graph-fit-and-smoothness.md`

## Acceptance Criteria

- `/graph` receives a route-scoped full-viewport page class; `/research`, Graph changes and other
  reading surfaces do not.
- At 1920×1080 the live Graph Studio is at least 95% of viewport width and materially wider than the
  1224px owner screenshot baseline.
- The graph canvas uses the available viewport height without hiding toolbar, notices, status bar or
  controls.
- Desktop, tablet and mobile retain zero page-level horizontal overflow.
- Fit view, progressive Hierarchy, Network/Orbit, Explorer and inspector behavior remain unchanged.

## Design Notes

- The layout change belongs in `AppShell`, where route identity is already known.
- Use responsive viewport-relative padding rather than negative-margin breakout CSS.
- The shared `.page` cap remains the default for every non-primary-graph route.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | AppShell applies the graph-only page class. |
| Integration | Graph page/CSS retains existing rendering behavior. |
| E2E | 1920×1080 width ratio plus responsive graph suite. |
| Platform | Live production screenshot/geometry and overflow audit. |
| Release | ESLint, TypeScript, focused/full frontend tests and build. |

## Harness Delta

Intake #76 and an owner-correction intervention record the screenshot-guided refinement. No API,
schema, canonical graph or deployment behavior changes.

## Evidence

- Owner screenshot `/home/linh/Pictures/Screenshots/Screenshot From 2026-08-14 10-04-20.png` at
  1920×1080 shows the studio from approximately x=341 to x=1565 (`1224px`, about 63.8% of the
  viewport), leaving more than 300px unused on both sides.
- Live production audit at the same 1920×1080 viewport:
  - main page width `1920px`, studio width `1862.4px` (`97.0%`), canvas `1860.4×864px`;
  - initial readable zoom `107%`, zero horizontal overflow and zero console/page errors;
  - screenshot: `/tmp/business-ai-graph-full-viewport-1920x1080.png`.
- `/graph` receives `page graph-page`; `/graph/changes` and other routes keep the default `.page`
  cap. Intervention #26 records the owner's screenshot correction.
- Full ESLint, 32 Vitest files / 144 tests, TypeScript and the 15-route production build pass.
  Responsive graph Playwright passes 3/3, with desktop running at 1920×1080 and asserting at least
  95% studio width plus zero overflow.
- Harness story verification/completion passed for intake #76; standard trace #78 records the
  implementation and live-production proof.
