# Exec Plan

## Goal

Make the accepted receipt contract true and verified in the application without starting Discord.

## Scope

In scope:

- Additive schema, safe backfill and guarded downgrade.
- Service-account create/list/revoke and bearer middleware scope enforcement.
- Receipt URL/document create/replay/read services and API.
- Legacy `/ingestion/links` dual-write compatibility.
- Audit/privacy, concurrency, storage cleanup, migration, API and browser proof.

Out of scope:

- Discord adapter/platform operations, webhook callbacks, production deployment execution and
  deletion of any legacy field/data/object.

## Risk Classification

Risk flags:

- Auth and authorization.
- Data model/migration.
- Audit/security.
- External system boundary.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Auth/authorization.
- Data migration and audit/security.

## Work Phases

1. Add story, models and guarded migration/backfill.
2. Implement service-account principal and operator lifecycle.
3. Implement receipt URL/document service and API.
4. Adapt legacy endpoint without breaking current response consumers.
5. Add deterministic tests for every accepted invariant.
6. Run migration/full suites, build/recreate runtime, verify live backfill and leave trace/logs.

## Stop Conditions

Pause for human confirmation if:

- Existing data would need deletion or reinterpretation.
- A bearer credential would need broader than intake-only scope.
- Receipt state would gain approval/publication authority.
- Discord implementation or production external mutation becomes necessary.

