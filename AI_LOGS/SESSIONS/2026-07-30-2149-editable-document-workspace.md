# Session Log

## Context

- User request:
  - Make Document workspace accept editable document formats such as DOCX, TXT and LaTeX and
    ensure AI can read their content.
  - For LaTeX, Markdown and similar source formats, provide raw and preview views side by side.
  - Preserve the earlier navigation change that hides Training data and labels the workspace
    correctly.
- Agent: Codex.
- Date/time: 2026-07-30 21:49 +07.
- Harness:
  - Intake #28 / normal story `US-DOCUMENT-EDITABLE-FORMATS`.
  - Intake #29 / high-risk story `US-DOCUMENT-SCOPED-CHAT-CONTEXT`.
  - Human correction/intervention #6 captured the scope expansion from navigation copy to
    document behavior.
  - Detailed trace #35 meets the high-risk 3/3 tier; final drift audit is `0/100`.

## Work Done

- Backend:
  - Expanded extension/MIME validation to PDF, DOCX, UTF-8 TXT, Markdown, LaTeX,
    reStructuredText, AsciiDoc and HTML.
  - Added streamed UTF-8/NUL checks, DOCX signature/OpenXML validation and bounded expanded/XML
    size checks.
  - Added bounded DOCX, LaTeX and HTML extractors; canonical extracted text continues through
    paper-fit, document graph and ResearchItem persistence.
  - Added `GET /api/v1/documents/{id}/content` with separate source and canonical text fields.
  - Added bounded canonical text to document-scoped chat under existing redaction and total
    context limits.
- Frontend:
  - Updated the upload picker and bilingual format guidance.
  - Added a safe document source viewer with Raw, Preview and Side-by-side modes.
  - Added structured Markdown/markup/LaTeX preview using controlled React elements; uploaded
    HTML is displayed only through extracted text and is never executed.
  - Added responsive source-view styles.
- Product/Harness docs:
  - Updated Graph Intelligence upload/API/implementation status and the project status report.
  - Added normal and high-risk story packets and completed both durable Harness stories.
- Files changed for this scope:
  - `apps/api/app/api/documents.py`
  - `apps/api/app/schemas/documents.py`
  - `apps/api/app/services/document_graph.py`
  - `apps/api/app/services/documents.py`
  - `apps/api/app/services/graph_chat.py`
  - `apps/api/tests/test_documents.py`
  - `apps/api/tests/test_graph_chat.py`
  - `apps/web/app/documents/page.tsx`
  - `apps/web/app/documents/page.test.tsx`
  - `apps/web/app/documents/[id]/page.tsx`
  - `apps/web/app/documents/[id]/page.test.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/components/document-source-viewer.tsx`
  - `apps/web/components/document-source-viewer.test.tsx`
  - `apps/web/lib/i18n.tsx`
  - `apps/web/lib/types.ts`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `Docs/Business AI Agents Project Status Report.md`
  - `docs/stories/editable-document-workspaces.md`
  - `docs/stories/document-scoped-chat-context/*`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - `AI_LOGS/SESSIONS/2026-07-30-2149-editable-document-workspace.md`

## Decisions Made

- Use a bounded allowlist rather than claiming universal editable-format support.
- Treat DOCX as bounded OpenXML and parse only canonical document XML; do not add a new office
  dependency or execute macros/embedded content.
- Return raw source only for validated UTF-8 source formats. DOCX/PDF keep their binary source
  downloadable but never place it in raw browser or chat context.
- Render previews using React text nodes and controlled elements, never `dangerouslySetInnerHTML`.
- Give document-scoped chat canonical extracted text only, with an inner bound plus the existing
  redaction/final context bound. This follows accepted DEC-019 and introduces no new retention or
  publication authority.
- No database migration was necessary; canonical content remains in the linked ResearchItem.

## Commands/Tests Run

- `scripts/bootstrap-harness.sh`
- Harness matrix, intake #28/#29, correction #6, story add/update/complete and trace preparation.
- `uv run ruff check app tests`
- `uv run python -m pytest tests/test_documents.py`
- `uv run python -m pytest tests/test_graph_chat.py`
- `uv run python -m pytest`
- `npm run lint`
- `npx tsc --noEmit`
- `npm run test`
- `npm run build`
- Docker Compose rebuild/recreate for API, worker and frontend with ports `18000/13000`.
- API health/readiness/OpenAPI/content endpoint smoke.
- Live system-Chrome inspection of an existing Markdown document workspace.

## Verification Result

- Backend Ruff: pass.
- Backend focused documents: 17/17 pass.
- Backend focused graph chat: 10/10 pass.
- Backend full suite: 257/257 pass.
- Frontend ESLint and TypeScript: pass.
- Frontend full suite: 71/71 pass.
- Next.js production build: pass, 15 routes.
- Runtime: database healthy; API, worker and frontend running; health `ok`; readiness `ready`;
  graph valid at 45 nodes / 32 edges; frontend `/documents` HTTP 200; fresh logs clean.
- Live Markdown workspace: Raw, Preview and Side-by-side controls present; no Training data link;
  no horizontal overflow.
- No real provider call was made during the new document-chat proof.

## Known Issues

- ODT, RTF and legacy `.doc` remain unsupported; they require separately accepted bounded parsers.
- Raw browser content is intentionally limited by `document_extract_max_chars`; the original file
  remains downloadable.
- In-browser source editing/version saving is not part of this slice; existing Research editor
  versioning remains separate.
- The legacy `.venv/bin/pytest` launcher has a stale historical shebang; verification used
  `uv run python -m pytest`, which passes.
- The frontend image's `npm install` reported 12 high-severity audit findings in the existing
  dependency tree. This session did not run destructive/breaking automated upgrades.
- The repository still contains extensive pre-existing uncommitted work unrelated to this change.

## Next Best Action

- Product owner uploads one real DOCX and one LaTeX/Markdown source, confirms extracted content and
  Raw/Preview/Song song behavior, then asks a document-scoped question in Brainstorm chat.
- If the desired next task is editing source inside Document workspace and saving file versions,
  define that as a separate versioning story rather than silently rewriting original attachments.
