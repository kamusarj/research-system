# Session Log

## Context

- User request: plan and implement selected-text AI editing inside uploaded documents, automatic
  document RAG, source versioning and refresh-safe editing while keeping human control.
- Agent: Codex
- Date/time: 2026-08-02 19:25 +07

## Work Done

- Files changed:
  - Backend domain/API: `apps/api/app/models.py`, `apps/api/app/schemas/documents.py`,
    `apps/api/app/api/documents.py`, `apps/api/app/services/document_editing.py`,
    `apps/api/app/services/document_rag.py`, `apps/api/app/services/document_processing.py`,
    `apps/api/app/services/document_graph.py`, `apps/api/app/services/documents.py`,
    `apps/api/app/services/search_projection.py`, `apps/api/app/services/graph_chat.py`.
  - Migration: `apps/api/migrations/versions/2d4e6f8a0b13_add_document_ai_edit_versions_rag.py`.
  - Backend proof: `apps/api/tests/conftest.py`, `apps/api/tests/test_document_editing.py`,
    `apps/api/tests/test_search_projections.py`.
  - Frontend: `apps/web/components/document-ai-editor.tsx`, document detail/source viewer,
    `apps/web/lib/documents.ts`, `apps/web/lib/types.ts`, `apps/web/lib/i18n.tsx`, responsive CSS,
    unit fixtures/tests and `apps/web/e2e/document-upload.spec.ts`.
  - Product/Harness truth: story packet `docs/stories/document-ai-edit-rag/`, ADR
    `docs/decisions/0024-human-reviewed-document-ai-edit-and-auto-rag.md`, README, implementation
    and Graph Intelligence plans, `AI_LOGS/DECISIONS.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/HANDOFF.md`.
- Behavior changed:
  - Markdown/TXT uploads can be edited after upload in Raw, Preview or Side-by-side mode.
  - Selecting text reveals Improve, Shorten, Expand, Fix grammar and custom AI actions.
  - Provider output is a draft comparison and mutates source only after explicit Accept; Reject is
    non-mutating. Stale source versions/selections fail closed.
  - Manual save, accepted AI edit and restore create immutable stored versions and requeue the
    document pipeline. Browser cache is scoped to user/workspace/base version and survives F5.
  - Successful extraction automatically replaces scoped pgvector chunks. Draft rows never appear
    in global approved search; document chat uses only the current indexed version.
  - Changed source invalidates prior document graph/evidence before evaluation so failed/low-fit
    rebuilds cannot leave stale facts visible.
- Commands run:
  - `bash scripts/bootstrap-harness.sh`; intake #35, story `US-DOCUMENT-AI-EDIT-RAG`, ADR 0024.
  - Changed-file Ruff format/check and 55 focused backend tests.
  - `cd apps/api && uv run python -m pytest -q --disable-warnings` (285 tests collected/passed).
  - Frontend ESLint, TypeScript, Vitest, production build and responsive Playwright proof.
  - PostgreSQL backup to `/tmp/research-pre-document-ai-edit.dump` and Alembic upgrade to head.
  - Rebuilt API/worker/frontend during feature rollout; rebuilt API/worker once more after the stale
    graph guard; health, migration, graph invariant, row-count and fresh-log checks.
  - `scripts/bin/harness-cli story complete US-DOCUMENT-AI-EDIT-RAG --json` (fresh proof pass).
  - Detailed high-risk Harness trace #41 recorded at tier 3/3.

## Reasoning / Decisions

- Decision: start post-upload editing with Markdown/TXT only; keep DOCX/PDF and other accepted
  formats read-only/previewable until byte-faithful rich-edit designs exist.
- Reason: source text can be safely versioned and diffed; rich binary/layout formats have different
  mutation, fidelity and recovery risks.
- Decision: AI creates a bounded, persisted proposal tied to exact version/range/hash, never an
  automatic overwrite.
- Reason: the repository's human-review contract and document sensitivity require explicit control.
- Decision: reuse pgvector instead of adding LightRAG or another store; automatically replace only
  the current document's chunks after successful extraction.
- Alternatives considered: immediate AI apply, body versions in PostgreSQL, separate vector table,
  background reprocessing of every migrated document and rich DOCX/PDF editing. All were rejected
  or deferred for governance, duplication, provider-cost or format-fidelity reasons.

## Verification

- Tests/checks: Ruff; 55 focused and 285 full backend tests; ESLint; TypeScript; 83/83 Vitest;
  Next.js 14-route production build; 9/9 Playwright at desktop/tablet/mobile; Harness fresh proof;
  runtime health/migration/graph/log checks.
- Result: pass. Live migration is `2d4e6f8a0b13 (head)`; direct and proxied health are `ok`, frontend
  is HTTP 200, graph invariants pass at 45 nodes / 32 edges, and no fresh API/worker error pattern
  was found.

## Known Issues

- Three pre-feature workspaces have version 1 backfilled and RAG status `pending`; each can use the
  new Rebuild action. New uploads and new source versions refresh RAG automatically.
- Rich round-trip editing for DOCX/PDF is not part of this phase. LaTeX/reStructuredText/AsciiDoc/
  HTML remain authorable before upload and safely viewable after upload, but not yet post-upload
  editable.
- LocalStorage cache is local, unencrypted and non-collaborative; server versions are durable truth.

## Next Agent Notes

- Continue from: product-owner browser acceptance at `http://localhost:13000/documents`.
- Watch out for: do not expose draft document chunks through global search and never log document
  text, selected text, replacement text or raw provider responses.
- Suggested next command: `docker compose ps && curl -fsS http://localhost:18000/api/v1/health`.
- Next best action: have the owner test one Markdown selection through proposal/Accept and decide
  whether the three legacy `pending` workspaces should be batch rebuilt.
