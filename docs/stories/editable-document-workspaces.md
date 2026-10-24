# US-DOCUMENT-EDITABLE-FORMATS - Editable document formats and source preview

## Status

implemented

## Lane

normal

## Product Contract

The Document workspace accepts a bounded set of editable research formats in addition to PDF,
extracts their readable content into the existing AI evaluation/graph/chat pipeline, and lets a
researcher inspect source-oriented formats as raw text, a safe formatted preview, or both side by
side.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Research System Implementation Plan.md`

## Acceptance Criteria

- Upload validation accepts DOCX, UTF-8 TXT, Markdown, LaTeX, reStructuredText, AsciiDoc and HTML
  alongside the existing PDF support, while rejecting extension/MIME mismatches and malformed
  binary documents.
- DOCX and text-source formats produce bounded canonical text that reaches the same paper-fit,
  document graph and document-scoped chat context used by existing uploads.
- A bounded content endpoint returns source text only for source-oriented UTF-8 formats and returns
  the canonical AI-readable text separately.
- Successfully extracted PDF/DOCX uploads expose their preserved original separately and their
  canonical text as an explicitly labelled editable derivative; saving never overwrites or
  mislabels the original binary bytes.
- Markdown, LaTeX and comparable source formats offer Raw, Preview and Side-by-side modes in the
  document detail UI.
- Preview rendering uses React text nodes and controlled elements; uploaded HTML or source markup
  is never executed as browser HTML or script.
- English and Vietnamese upload/preview copy identifies the supported formats and content states.

## Design Notes

- Commands: existing `POST /api/v1/documents`; new read-only
  `GET /api/v1/documents/{id}/content`.
- Queries: document detail loads content only for the selected workspace.
- API: return `source_text`, `extracted_text`, `format`, `supports_raw` and `preview_kind`.
- Tables: no schema change; canonical extracted content remains in the linked `ResearchItem`.
- Domain rules:
  - 20 MB upload bound remains unchanged.
  - Text source formats must be UTF-8 and contain no NUL bytes.
  - DOCX is a bounded OpenXML ZIP and must contain `word/document.xml`.
  - AI prompts consume canonical extracted text, never binary bytes.
  - Binary version 1 remains the immutable upload; later PDF/DOCX workspace versions are UTF-8
    derivatives processed as text under the same optimistic version/RAG workflow.
- UI surfaces: `/documents` upload picker and `/documents/{id}` source viewer.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Text/DOCX extraction, MIME/signature validation and safe preview parsing tests. |
| Integration | Upload -> worker -> canonical research content -> content endpoint for DOCX/LaTeX. |
| E2E | Live browser confirms source view modes and supported upload copy. |
| Platform | Existing local Compose runtime serves the updated frontend/API after rebuild. |
| Release | Focused backend/frontend suites, Ruff, ESLint, TypeScript and production build pass. |

## Harness Delta

No Harness policy change is expected.

Follow-up story `US-DOCUMENT-AUTHORING-CACHE` adds direct source authoring and
per-user refresh-safe browser drafts while reusing this story's governed upload
and preview contracts.

## Evidence

- Backend: Ruff passes; full Pytest passes 257/257, including 17 document tests for DOCX
  OpenXML validation/extraction, malformed containers, LaTeX canonical text and the content API.
- Frontend: ESLint and TypeScript pass; 71/71 Vitest tests pass; the 15-route production build
  passes.
- Runtime: API/worker/frontend images rebuilt; API health is `ok`, readiness is `ready`, frontend
  `/documents` returns HTTP 200 and fresh logs contain no errors.
- Live Chrome: an existing Markdown workspace exposes Raw, Preview and Side-by-side controls,
  retains zero horizontal overflow with the renamed Document workspace navigation.
