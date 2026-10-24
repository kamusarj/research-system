# System map foreground label layer

## Context

- User request: apply the same covered-text fix to `http://localhost:13000/graph/system`.
- Agent: Codex
- Date/time: 2026-08-14 15:24 +07
- Harness: intake #79, normal story `US-SYSTEM-MAP-FOREGROUND-LABELS`, owner-correction
  intervention #28 and standard trace #81.

## Files Changed

- `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`
- `apps/web/app/globals.css`
- `apps/web/e2e/system-graph.spec.ts`
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/stories/system-map-foreground-labels.md`
- `AI_LOGS/HANDOFF.md`
- `AI_LOGS/TASKS.md`

## Decisions Made

- Scoped the overlay to hierarchy data containing both `SystemRoot` and `SystemPillar`, leaving the
  primary research hierarchy and Network community behavior unchanged.
- Kept every interactive/card source group and its accessible name, but visually hid its direct
  text and mirrored that text into the existing foreground SVG label group.
- Made overlays pointer-transparent and added a restrained 2.5px canvas-colored outline so text
  remains readable without changing card geometry, layout, containment, folding or selection.

## Commands and Tests Run

- Required startup reads, Harness bootstrap, active matrix query and live route inspection.
- Focused ESLint, 18 renderer/system/visualization Vitest tests and TypeScript: passed.
- Production Next build: passed, 15 routes.
- Rebuilt and recreated the multi-user frontend with health wait: passed.
- Responsive Playwright desktop/tablet/mobile: 3/3 passed, including Harness completion rerun.
- Full frontend ESLint and 32 files / 144 Vitest tests: passed.
- Live system Chrome audit at 1920x1080: 12 nodes/overlays collapsed, 45 expanded, correct foreground
  order, 2.5px stroke, no horizontal overflow and no console/page errors.

## Verification Result

- `/graph/system` now paints visible type, title, action/count and child labels after all cards.
- Expanded children remain inside their compound pillar and the 12 -> 45 -> 12 interaction contract
  remains covered by E2E.
- Frontend is rebuilt and healthy at `http://localhost:13000/graph/system`; API remains on `18000`.
- Temporary system-map screenshots used for inspection were removed from `/tmp`.

## Known Issues

- None introduced by this fix.
- The first standalone live-audit launch looked for Playwright's uninstalled bundled Chromium; the
  repository-configured system Chrome channel was then used successfully.

## Next Best Action

- Owner refreshes `/graph/system`, expands Data, Knowledge & Memory and confirms labels remain
  readable at their preferred zoom level.
