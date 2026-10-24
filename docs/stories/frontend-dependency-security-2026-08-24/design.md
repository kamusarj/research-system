# Design — Frontend dependency security patch

## Domain Model

No domain or data-model change.

## Application Flow

Keep application source and routes unchanged. Resolve the runtime dependency graph to Next.js
15.5.23, matching `eslint-config-next`, and patched transitive packages.

## Interface Contract

All existing routes, proxy rewrites, response behavior and frontend scripts remain stable.

## Data Model

No schema, migration, stored data or retention change.

## UI / Platform Impact

- Runtime stays on Node 22, which satisfies patched package engine requirements.
- Frontend image is rebuilt and recreated only after all local checks pass.
- `sharp`, `postcss`, and `nanoid` overrides are explicit because the Maintenance LTS package's
  transitive ranges otherwise retain versions named by the current audit.

## Observability

Record npm audit output, resolved dependency versions, build output, responsive Playwright results,
HTTP health/readiness and fresh frontend logs.

## Alternatives Considered

1. Upgrade to Next.js 16. Rejected because the official Maintenance LTS patch exists and a major
   migration adds unrelated behavioral risk.
2. Ignore transitive findings because the stack is local. Rejected because the production image
   includes and may execute these packages.
3. Run `npm audit fix --force`. Rejected because an explicit bounded manifest is reviewable and does
   not permit an uncontrolled major upgrade.
