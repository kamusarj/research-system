# Exec Plan

## Goal

Find and fix all frontend-owned defects that can be reproduced through the repository's complete static, unit, production-build, browser-route and responsive validation surfaces.

## Scope

In scope:

- ESLint and TypeScript errors.
- Failing frontend unit/component tests.
- Next.js production build errors.
- Hydration, uncaught runtime, console error and failed same-origin API behavior on current routes.
- Broken navigation and primary interactions covered by existing browser tests.
- Desktop, tablet and mobile page-level overflow.
- Missing regression coverage for each defect fixed.

Out of scope:

- Backend/data/provider mutations.
- New product features unrelated to a reproduced defect.
- Optional external services that are intentionally disabled.

## Risk Classification

Risk flags:

- Public contracts.
- Cross-platform.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None, provided the implementation remains frontend-only and does not weaken validation.

## Work Phases

1. Capture static/unit/build/runtime baseline.
2. Inventory distinct reproducible failures.
3. Read the smallest affected route/component contract for each failure.
4. Add a failing regression test where practical and implement the smallest frontend fix.
5. Re-run focused proof after each fix.
6. Run the complete validation ladder and inspect live runtime logs/routes.
7. Update Harness proof and cross-agent logs.

## Stop Conditions

Pause for human confirmation if:

- A fix requires changing backend API/schema/data or authorization behavior.
- A product interaction has multiple materially different valid outcomes.
- A required test must be weakened or skipped.
- The requested sweep expands into a new feature or visual redesign.
