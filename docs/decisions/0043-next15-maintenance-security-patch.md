# 0043 Keep the frontend on patched Next.js 15 Maintenance LTS

Date: 2026-08-24

## Status

Accepted

## Context

A full-project sweep found four high-severity production dependency findings in Next.js 15.5.20 and
its `sharp`, `postcss`, and `nanoid` tree. Official Next.js guidance identifies 15.5.21 or newer as
the patched Maintenance LTS line for the July 2026 security release, while npm currently resolves a
newer 15.5 patch. A Next.js 16 migration is not required to remove the current findings.

## Decision

Stay on Next.js major 15, update Next.js and `eslint-config-next` to the current 15.5 patch, and use
bounded manifest overrides for patched `sharp`, `postcss`, and `nanoid` versions when the upstream
Maintenance LTS dependency ranges still resolve vulnerable releases. Require zero high/critical
production audit findings plus full frontend unit/build/E2E/runtime proof.

## Alternatives Considered

1. Move to Next.js 16 immediately. Rejected as an unrelated major migration with wider regression
   risk.
2. Accept transitive findings on a trusted-local host. Rejected because the packages ship in the
   production frontend image.
3. Use an uncontrolled forced audit fix. Rejected in favor of explicit version bounds and proof.

## Consequences

Positive:

- Current known high-severity findings are removed without a framework-major migration.
- The lockfile makes the patched runtime graph reproducible.

Tradeoffs:

- Overrides must be rechecked when Next.js changes its dependency ranges.
- The separate Next.js security release announced for 2026-08-26 requires a fresh audit after it is
  published; this decision cannot cover an unavailable patch.

## Follow-Up

- Run `npm audit --omit=dev --audit-level=high` after the announced 2026-08-26 release and apply the
  newest Maintenance LTS patch if needed.
