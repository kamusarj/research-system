# Exec Plan

## Goal

Lock an implementable, source-neutral occurrence/receipt contract before Discord Gate D while
preserving existing intake behavior and provenance.

## Scope

In scope:

- Domain entities, idempotency and concurrency invariants.
- URL/document item lifecycle and durability rules.
- API, auth/privacy/audit, additive migration and rollout contracts.
- Required verification and Gate D entry criteria.
- Product docs, durable decision, Harness story/proof, and AI handoff updates.

Out of scope:

- Application schema/code, runtime data migration, service accounts, bot code, Discord credentials,
  webhooks, live platform calls, and production deployment.

## Risk Classification

Risk flags:

- Data model.
- Audit/security.
- External systems.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Audit/security.
- External provider/platform behavior.

## Work Phases

1. Inspect current URL uniqueness, duplicate behavior, source provenance and Gate D requirements.
2. Define receipt/item boundaries, deterministic keys, privacy and concurrency invariants.
3. Define API, migration, attachment durability, authorization and validation contracts.
4. Update authoritative product docs and record the architectural decision.
5. Run static structure/fence/consistency checks.
6. Record Harness proof/trace and update cross-agent logs.

## Stop Conditions

Pause for human confirmation if:

- The adapter is asked to own extraction/publication business logic.
- The design requires deleting or rewriting legacy intake provenance.
- Discord implementation is requested before Graph v2/Gate C entry criteria are met.
- Validation or service-account isolation would need to be weakened.

