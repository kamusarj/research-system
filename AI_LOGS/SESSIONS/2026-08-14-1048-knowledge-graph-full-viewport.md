# Knowledge Graph full-viewport layout

## Context

- User request: use the supplied screenshot to make the Knowledge Graph display larger and fit the
  screen.
- Agent: Codex
- Date/time: 2026-08-14 10:48 +07

## Work Done

- Files changed:
  - `apps/web/components/app-shell.tsx`
  - `apps/web/components/app-shell.test.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/e2e/graph-hierarchy.spec.ts`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `docs/stories/knowledge-graph-full-viewport.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - The primary `/graph` route receives a dedicated `graph-page` shell class.
  - That route alone removes the shared 1440px maximum and uses 0.75–1.8rem responsive gutters.
  - Wide-screen graph canvas height grows up to 80dvh/880px; tablet/mobile rules stay unchanged.
  - `/graph/changes`, Research, Documents and every other route retain the shared reading width.
- Commands run:
  - Required Harness bootstrap, intake #76, story lifecycle and intervention #26.
  - Screenshot inspection with original detail.
  - Focused and full ESLint/Vitest, TypeScript and Next production build.
  - Responsive Playwright across desktop 1920×1080, tablet and mobile.
  - Production frontend recreation with health wait.
  - Live Chrome geometry/overflow/console audit and screenshot capture.

## Reasoning / Decisions

- Decision: apply the width change in AppShell using route identity, not a global `.page` change.
- Reason: the graph benefits from spatial width; reading and review surfaces still benefit from a
  bounded line length.
- Decision: use normal responsive padding instead of negative-margin full bleed.
- Reason: it gives a predictable 97% wide-screen result without risking horizontal overflow.
- Decision: preserve readable initial graph zoom and Fit behavior.
- Reason: the owner's issue was unused viewport space, not a request to shrink or hide graph nodes.

## Verification

- Screenshot baseline at 1920×1080: studio approximately `1224px` (`63.8%`) with more than 300px
  unused on both sides.
- Live final geometry at 1920×1080: main `1920px`, studio `1862.4px` (`97.0%`), canvas
  `1860.4×864px`, zoom `107%`, horizontal overflow `0`, browser errors `0`.
- Visual proof: `/tmp/business-ai-graph-full-viewport-1920x1080.png`.
- Full frontend: ESLint passed; 32 files / 144 Vitest tests passed; TypeScript passed; 15-route
  production build passed.
- Responsive Playwright: desktop/tablet/mobile 3/3 passed; desktop runs at the owner's 1920×1080
  size and enforces the 95% minimum width.
- Runtime: rebuilt standalone frontend is healthy on `13000`; API remained ready on `18000`.
- Harness: story verification/completion passed; intervention #26 records the owner correction and
  standard trace #78 records the implementation and live-production proof.

## Next Agent Notes

- Continue from: `http://localhost:13000/graph` is live with the full-viewport shell.
- Watch out for: do not apply `graph-page` to `/graph/changes`; its review content should remain
  readable and bounded.
- Suggested check: `cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/graph-hierarchy.spec.ts`.
