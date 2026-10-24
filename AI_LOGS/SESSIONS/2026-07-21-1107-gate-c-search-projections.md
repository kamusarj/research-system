# Session Log

## Context

- User request: set up and use Repository Harness, read `AI_LOGS`, establish the durable completion
  goal and continue completing the project.
- Agent: Codex (`/root`).
- Date/time: 2026-07-21 11:07 +07.

## Work Done

- Files changed: search/vector settings, models, schemas, routes and projection service; Alembic
  migration `c5a8e2f4b901`; real projection verifier and tests; API dependency lock; digest-pinned
  pgvector/Meilisearch Compose configuration and managed-secret overlay; README/product architecture,
  completion plan, implementation plan, Harness story/decision docs and AI handoff logs.
- Behavior changed: an owner can explicitly rebuild approved-only Meilisearch and pgvector
  projections. Meilisearch uses validated staging plus atomic swap. Semantic search uses real bounded
  Mistral embeddings stored as `vector(1024)` with HNSW cosine lookup. Both selected providers fail
  visibly and results are hydrated from current canonical PostgreSQL rows. Local defaults remain
  PostgreSQL/lexical.
- Harness: recorded intake #10, decision 0013, completed high-risk story
  `US-GATEC-SEARCH-PROJECTIONS`, recorded detailed trace #13 and audited at entropy 5/100; the only
  unverified story is the external product-owner `US-GV2-ACCEPT` gate.
- Commands run: Harness bootstrap/intake/story/decision/query/verify/complete/trace/audit; Ruff; full
  Pytest; migration parity; frontend ESLint/TypeScript/Vitest/Playwright; Docker image pulls/builds,
  Compose base/search/secret-overlay validation, logical `pg_dump`, live PostgreSQL migration, real
  Meilisearch/Mistral/pgvector proof, health/count/log checks and Markdown fence/diff checks.

## Reasoning / Decisions

- Decision: PostgreSQL remains the only canonical authority; both search stores are independently
  rebuildable projections.
- Reason: external index freshness must not override research lifecycle/content, and the legacy
  SHA-derived JSON arrays are not semantic retrieval evidence.
- Alternatives considered: legacy vectors, in-place live-index rebuild, Meilisearch as response
  authority, automatic silent fallback and a simulated distributed transaction were rejected.

## Verification

- Tests/checks: Ruff and 141 backend tests; SQLite migration check/round trip; 28 frontend tests;
  ESLint and TypeScript; 30 Playwright desktop/tablet/mobile cases; base/search/secret-overlay Compose;
  direct and proxied health; live PostgreSQL extension/schema/index; three real projection rebuilds,
  injected stale data, lexical read, semantic read and canonical parity.
- Result: pass. Live proof produced 3 Meilisearch documents, 3 vector documents / 9 chunks at 1024
  dimensions, one HNSW index, zero stale rows and unchanged 8 canonical / 3 approved counts. The main
  stack is healthy on API 18000/frontend 13000. The exact temporary logical dump and disposable
  Meilisearch containers/volumes were removed after validation; they are rebuildable from canonical
  PostgreSQL. No user data, secret value or unrelated `smart_exam_*` resource was changed.

## Next Agent Notes

- Continue from: replace the rejected OpenAI secret outside source control, recreate API and execute
  the two real chat steps in the product-owner acceptance checklist; only the product owner accepts.
- Watch out for: search projection freshness is still an explicit owner operation; production owns
  Meilisearch key scoping, TLS/network policy, capacity and backup. The local host still requires
  `API_PORT=18000 FRONTEND_PORT=13000` because unrelated `smart_exam_backend` owns port 8000.
- Known issues: current OpenAI credential returns typed `CHAT_PROVIDER_UNAVAILABLE`; external MinIO
  migration/backup, telemetry retention/alerts, secret rotation and TLS/egress remain deployment work.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`.
