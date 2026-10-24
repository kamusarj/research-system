# Exec Plan

## Goal

Remove the Training Data Hub and its persisted domain from the active Research
System without disturbing research, document, search, graph, collector, or
authentication data.

## Scope

In scope:

- Remove the `/training` frontend route and all Training Data UI copy.
- Remove the `/api/v1/training/*` API and its authorization rules.
- Remove Training Data ORM models, seed behavior, tests, and active documentation.
- Add a head migration that drops all six Training Data tables and their rows.
- Prove the migration is reversible at the schema level and that the retired
  routes return `404`.

Out of scope:

- Removing generic AI model evaluation or learning terminology unrelated to the
  Training Data Hub.
- Rewriting immutable historical migrations, decisions, session logs, or source
  brainstorm artifacts.
- Preserving or exporting the rows the user explicitly requested to delete.

## Risk Classification

Risk flags:

- Data model and data loss.
- Authorization.
- Public contracts.
- Existing behavior.
- Multi-domain frontend/backend/documentation change.

Hard gates:

- Destructive schema migration.

## Work Phases

1. Inventory active routes, models, tables, records, tests, and docs.
2. Record the retirement decision and deletion boundary.
3. Remove the feature from frontend and backend code.
4. Add and apply the destructive head migration.
5. Run backend, frontend, build, migration, and runtime route checks.
6. Update story proof, Harness trace, and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- Any Training Data table is referenced by another active product domain.
- The deletion would remove research, document, search, graph, collector, auth,
  or audit records.
- Validation would require editing historical migrations.
