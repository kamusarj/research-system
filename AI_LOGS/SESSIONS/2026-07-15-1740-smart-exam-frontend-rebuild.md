# Session Log

## Context

- User request: rebuild the Research System frontend following the UI of `/home/linh/smart-exam-ai`.
- Agent: Codex
- Date/time: 2026-07-15 17:40 Asia/Bangkok

## Work Done

- Files changed:
  - `apps/web/components/app-shell.tsx`: replaced the sidebar with the Smart Exam topbar, icon navigation, language control, CTA and responsive route strip.
  - `apps/web/app/globals.css`: rebuilt shared tokens and responsive styles around the reference ivory/red-orange design system.
  - Dashboard, research detail, search, gaps, collector and training pages; existing intake, research library and graph were restyled by the shared system.
  - `apps/web/lib/i18n.tsx`, graph theme, icon, Playwright config/spec, package manifest/lock and root layout.
  - `docker-compose.yml`, `.env.example`, `README.md`, `AI_LOGS/DECISIONS.md`, `HANDOFF.md` and `TASKS.md`.
- Behavior changed:
  - All product workspaces now share the Smart Exam typography, palette, surfaces, pills, forms, tables and state treatments.
  - Navigation remains complete on desktop, tablet and mobile; EN/VI switching remains persistent.
  - Inter is self-hosted with `@fontsource/inter`.
  - Local Compose always uses the relative API proxy instead of inheriting a stale browser-facing host URL.
- Commands run:
  - Inspected reference source/CSS and captured reference/current screenshots with Chrome and Playwright.
  - `npm install @fontsource/inter`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, and `E2E_BASE_URL=http://localhost:13000 npm run test:e2e`.
  - Rebuilt/recreated the frontend image, checked real root HTML, container logs, proxy health, Compose config and runtime environment.

## Reasoning / Decisions

- Decision: preserve Research System information architecture and behavior, but adopt the Smart Exam visual language directly instead of approximating it with the previous sidebar workspace.
- Reason: this satisfies visual consistency without coupling Research code to Smart Exam business logic.
- Decision: improve the reference responsive breakpoint by retaining a scrollable mobile navigation row, because Research has eight primary routes.
- Decision recorded as `DEC-014`.

## Verification

- Tests/checks: ESLint, TypeScript, 12 Vitest tests, Next.js production build, npm audit, 12 Playwright cases on desktop/tablet/mobile, manual screenshots of all routes, Docker image/runtime/proxy checks.
- Result: all final checks passed. Playwright covers all eight primary routes, exact design tokens, translated status badges, multi-source submission and no horizontal overflow. Runtime frontend is available on port 13000 and API proxy health passes.

## Known Issues

- Authentication/account UI from Smart Exam was not copied because Research System has no auth domain yet; auth/RBAC remains Gate C work.
- The current Compose frontend runs Next.js dev mode by project convention; the production Next.js build itself passes.
- Default API port 8000 remains occupied by the unrelated Smart Exam backend, so Research System continues on 18000/13000.

## Next Agent Notes

- Continue from: product-owner visual acceptance, then the planned receipt/occurrence model before Discord work.
- Watch out for: do not reintroduce a host `NEXT_PUBLIC_API_URL` into base Compose; use the `/api/v1` frontend proxy locally.
- Suggested next command: `E2E_BASE_URL=http://localhost:13000 npm --prefix apps/web run test:e2e`.
