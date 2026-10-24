# US-WEB-SHARED-FOOTER Add a Shared Landing-Style Footer

## Status

implemented

## Lane

normal

## Product Contract

Every Research System workspace route renders one compact footer after its main content. It keeps
only the product name, three primary navigation links, and copyright. Navigation labels follow the
active English/Vietnamese locale. The footer remains readable and free of horizontal overflow on
desktop, tablet, and mobile.

## Relevant Product Docs

- `README.md`
- `Docs/Research System Implementation Plan.md`
- `Docs/Research System MVP Specification.md`

## Acceptance Criteria

- The shared `AppShell` renders exactly one semantic footer below the main content on every
  workspace route.
- The footer contains only the Research System name, Research/Sources/Knowledge graph links, and
  copyright.
- Navigation labels switch with the existing EN/VI locale.
- Internal links use Next.js navigation and lead to existing workspace routes.
- The footer aligns with the deep-ocean shell and collapses cleanly without horizontal overflow on
  tablet/mobile.
- Focus-visible and hover states remain clear against the dark surface.

## Design Notes

- Commands: none.
- Queries: none.
- API: unchanged.
- Tables: unchanged.
- Domain rules: unchanged.
- UI surfaces: `AppShell`, shared i18n messages, global responsive styles, and focused shell tests.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Shared shell test proves semantic footer, brand, grouped links, and bottom-bar copy. |
| Integration | Not applicable; no API or persistence boundary changes. |
| E2E | Existing all-route and no-overflow browser coverage remains compatible. |
| Platform | Next.js production build and responsive CSS review. |
| Release | Frontend lint, typecheck, unit tests, and production build. |

## Harness Delta

Intake #21 introduced the footer. Intake #22 and correction intervention #4 record the product
owner's request to remove the decorative glow, long description, grouped headings, product
principle, and excess links. No durable architecture decision is needed.

## Evidence

- `AppShell` owns one semantic footer after the shared main-content container, so all current and
  future workspace routes inherit it without page-level duplication.
- The corrected footer is one compact flex row with the product name, three core links and
  copyright; it wraps into two short rows on mobile.
- Unused footer description/group/principle translation keys and decorative CSS were removed.
- Focused shell test: 1 passed.
- Complete frontend unit suite: 21 files / 67 tests passed.
- ESLint, TypeScript, and `git diff --check` passed.
- Next.js production build passed all 15 routes.
- Focused Playwright proof passed desktop, tablet, and mobile (3/3) with no horizontal overflow.
- After correction intervention #4, the full 67-test suite, ESLint, TypeScript, 15-route build and
  three-viewport focused Playwright proof passed again for the compact version.
