# Exec Plan

## Goal

Deliver a safe Markdown/TXT document editor with inline AI rewrite proposals,
durable source history and automatic document-scoped RAG refresh.

## Scope

In scope:

- Source versions, manual save and restore.
- Selection-based AI proposals with explicit Accept/Reject.
- Per-user/workspace/version F5-safe editor cache.
- Automatic per-document pgvector refresh and retry/status UI.
- Backend, frontend, migration, E2E and runtime proof.

Out of scope:

- DOCX/PDF rich editing.
- Collaborative editing or automatic conflict merge.
- AI auto-apply and canonical graph auto-publication.

## Risk Classification

Risk flags:

- Authorization, data model/migration, audit/security, external provider,
  additive public API, existing document/search/chat behavior and multi-domain UI.

Hard gates:

- Durable source ownership, provider-bound document content and audit safety.

## Work Phases

1. Record story, decision and migration contract.
2. Implement models/schemas/services/APIs and automatic RAG refresh.
3. Implement responsive editor, cache, proposal diff and version controls.
4. Add deterministic provider/storage/vector tests and browser proof.
5. Run migrations, focused/full verification and runtime smoke.
6. Update product truth, Harness trace and AI handoff logs.

## Stop Conditions

Pause for human confirmation if implementation requires deleting or rewriting
historical objects, bypassing explicit AI acceptance, weakening role/CSRF checks,
or broadening rich editing beyond Markdown/TXT.

