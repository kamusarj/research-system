# Session Log

## Context

- User request: Continue immediately with the next Graph Intelligence implementation step.
- Agent: Codex.
- Date/time: 2026-07-18 11:17 +0700.

## Work Done

- Files changed:
  - `apps/api/app/models.py`
  - `apps/api/migrations/versions/d7e3b9a1f604_add_document_processing_graph.py`
  - `apps/api/app/schemas/documents.py`
  - `apps/api/app/schemas/paper_fit.py`
  - `apps/api/app/services/document_graph.py`
  - `apps/api/app/services/document_processing.py`
  - `apps/api/app/services/documents.py`
  - `apps/api/app/services/ai.py`
  - `apps/api/app/api/documents.py`
  - `apps/api/app/core/config.py`
  - `apps/api/app/worker.py`
  - `apps/api/tests/conftest.py`
  - `apps/api/tests/test_documents.py`
  - `apps/api/tests/test_ai_collector.py`
  - `apps/web/lib/types.ts`
  - `apps/web/lib/documents.ts`
  - `apps/web/lib/i18n.tsx`
  - `apps/web/app/documents/page.tsx`
  - `apps/web/app/documents/[id]/page.tsx`
  - `apps/web/app/documents/[id]/page.test.tsx`
  - `apps/web/components/document-graph-canvas.tsx`
  - `apps/web/components/document-graph-canvas.test.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/e2e/document-upload.spec.ts`
  - `.env.example`
  - `docker-compose.yml`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - Uploaded workspaces are automatically claimable by the combined worker with leases, retry backoff and expired-lease recovery.
  - Markdown/plain text and PDF text layers are extracted with page/character bounds; scanned PDFs produce an explicit limitation and hard-gate result without fake AI content.
  - The selected provider supplies typed semantic paper-fit dimensions, while backend code calculates hard gates, weighted score and routing.
  - Evaluation and provider/model/prompt/input-hash provenance are persisted in `paper_evaluations` and `ai_outputs`.
  - Papers at score 60 or above receive a bounded isolated document graph; structural nodes are server-created and AI semantic evidence must match the source verbatim or remain `evidence_pending`.
  - Added analyze/retry/evaluation/graph APIs plus `/documents/{id}` evaluation, provenance, graph and evidence UI.
  - OpenAI Responses requests now explicitly set `store: false`; source content is marked as untrusted prompt data.
- Commands run:
  - `.venv/bin/python -m ruff check app tests`
  - `.venv/bin/python -m pytest -q`
  - `.venv/bin/python -m alembic upgrade head`
  - `.venv/bin/python -m alembic downgrade a4f1c7d9e205`
  - `npm run lint`
  - `npm run typecheck`
  - `npm run test -- --run`
  - `npm run build`
  - `E2E_BASE_URL=http://localhost:3100 npx playwright test e2e/document-upload.spec.ts`
  - `docker compose config -q`
  - `git diff --check`

## Reasoning / Decisions

- Decision: Process new uploads automatically while retaining explicit analyze/retry endpoints.
- Reason: Upload-to-graph should be zero-extra-step in normal operation, while state-safe manual recovery remains available.
- Decision: Only build a document graph for a server-calculated score of at least 60 and no failed hard gate.
- Reason: This implements the accepted routing policy and avoids presenting irrelevant or unreadable sources as graph-ready.
- Decision: Keep structural Document/Section nodes deterministic and allow the provider to propose only semantic nodes/edges.
- Reason: Source containment and offsets are facts owned by extraction code, not model judgment.
- Decision: Match AI evidence against source text with whitespace-tolerant verbatim validation.
- Reason: A graph item must be grounded or visibly marked `evidence_pending`; the model cannot invent proof.
- Decision: Set `store: false` for the shared OpenAI Responses adapter.
- Reason: Current official OpenAI documentation states Responses are stored by default unless storage is explicitly disabled, matching DEC-018's retention default.

## Verification

- Tests/checks:
  - Backend: 67 Pytest tests and Ruff.
  - Frontend: ESLint, TypeScript, 19 Vitest tests and Next.js production build.
  - Migration: `d7e3b9a1f604` upgrade/downgrade/upgrade on temporary SQLite, with workspace/node/edge tables present.
  - E2E: upload plus processed paper-fit/graph/evidence on desktop, tablet and mobile; six cases passed.
  - Compose config and diff whitespace checks.
- Result: All checks passed. Pytest reports only the existing Starlette/httpx deprecation warning. The running Docker/PostgreSQL stack was not rebuilt.

## Known Issues

- OCR is not implemented; PDFs without a readable text layer stop at an explicit hard-gate review.
- Document graphs remain isolated and cannot mutate canonical knowledge; Phase 4 mapping/change-set review is next.
- The host `.venv/bin/alembic` launcher still has its old shebang; migration verification succeeds through `.venv/bin/python -m alembic`.

## Next Agent Notes

- Continue from: exact label/alias candidate retrieval and typed mapping proposals from document nodes into draft graph change sets.
- Watch out for: no canonical mutation before validation and explicit review; change-set apply must be transactional and idempotent.
- Suggested next command: `cd apps/api && .venv/bin/python -m pytest -q tests/test_documents.py tests/test_ontology.py`.
