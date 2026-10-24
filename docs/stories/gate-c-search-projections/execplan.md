# Exec Plan

## Goal

Deliver real, idempotent Meilisearch and pgvector adapters with repeatable parity/failure proof while
preserving PostgreSQL ownership and existing frontend contracts.

## Scope

In scope:

- Search projection schemas, repository/service boundaries and owner rebuild API.
- Meilisearch atomic staging/swap and selected-provider lexical/suggest reads.
- Real Mistral query/document embeddings plus pgvector cosine retrieval.
- PostgreSQL migration, pgvector-capable database image, internal-only Meilisearch profile, secret
  configuration, tests, verifier and operator docs.

Out of scope:

- Automatic outbox consumers, cross-service transactions and zero-lag guarantees.
- Multi-tenant search rules, browser-held Meilisearch keys or public service ports.
- Re-embedding historical non-approved artifacts or benchmarking general-world relevance.

## Risk Classification

Risk flags:

- Data model and migration.
- External systems/provider behavior.
- Public API/provider-selection contracts.
- Existing search behavior.
- Weak current semantic proof.

Hard gates:

- External provider behavior.
- Migration/data preservation.

## Work Phases

1. Capture current search/vector state and official provider behavior.
2. Lock the provider, atomicity, data-ownership and failure contract.
3. Add schemas/migration/configuration and deterministic boundary tests.
4. Implement rebuild and selected-provider reads.
5. Back up, migrate and exercise real pgvector/Meilisearch/Mistral paths.
6. Run regression/platform proof and update Harness/product/AI logs.

## Stop Conditions

Pause for human confirmation if:

- Existing PostgreSQL data cannot be backed up or major-version compatibility is uncertain.
- The migration would delete or reinterpret legacy embeddings.
- A real embedding provider cannot return the required fixed dimension.
- Completing the story would require exposing a provider port/key to the browser.
- Validation requirements would need to be weakened.
