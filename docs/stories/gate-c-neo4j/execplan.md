# Exec Plan

## Goal

Replace the explicit Neo4j scaffold with a real, idempotent and bounded graph projection adapter,
then prove relationship/hierarchy parity against PostgreSQL without changing the source of truth.

## Scope

In scope:

- Official Neo4j Python driver and bounded configuration.
- Composite constraints, atomic batched rebuild, stale-row pruning and parity counts.
- Existing graph query contract served from the selected Neo4j provider.
- Owner-only rebuild behavior, optional internal-only Compose service and operator docs.
- Unit/integration/runtime proof for idempotency, stale deletion, failures and parity.

Out of scope:

- Meilisearch, pgvector, Redis or Discord.
- Neo4j canonical writes, automatic publication, or public API schema changes.
- Production clustering, Aura provisioning, TLS certificates, backup or capacity policy.

## Risk Classification

Risk flags:

- Data model: a new external projection schema and stale-row lifecycle.
- External systems: Neo4j driver/service and credentials.
- Existing behavior: selected-provider graph reads and rebuild semantics change.
- Weak proof: the current scaffold has no real service/parity evidence.

Hard gates:

- External provider behavior.
- Rebuild must never mutate or delete canonical PostgreSQL knowledge.
- No silent fallback or weakened graph validation.

## Work Phases

1. Inspect accepted projection requirements and current repository boundary.
2. Record the projection identity/transaction/failure decision.
3. Implement the official driver adapter and explicit rebuild path.
4. Add optional deployment wiring and operator documentation.
5. Run deterministic tests plus disposable real-Neo4j parity/idempotency proof.
6. Record Harness evidence, trace and AI handoff state.

## Stop Conditions

Pause for human confirmation if:

- Neo4j would need to become a canonical write path.
- Existing graph API behavior must be removed or weakened.
- Projection rebuild would delete anything outside its own labeled rows.
- Validation requires production credentials, externally hosted infrastructure or destructive
  canonical migration.
