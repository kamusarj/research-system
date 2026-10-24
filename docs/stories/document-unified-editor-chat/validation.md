# Validation

## Proof Strategy

Prove source/range/history bounds and provider payloads with deterministic doubles, then exercise
editable import, contextual Send and explicit local apply separately from Create/Save. Preserve the
existing upload, immutable version, RAG and selection-edit proof.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | UTF-8 format mapping/import; context selection; request range/history bounds; local apply modes. |
| Integration | Stateless provider response/provenance; redacted bounded payload; no chat/document row mutation; all editable source formats save versions. |
| E2E | Import source into Document content without upload, brainstorm, append/replace explicitly, create, and brainstorm in uploaded editor. |
| Platform | Wide desktop, 1366px Windows, tablet/mobile stacking; production build and rebuilt runtime. |
| Performance | 20 MB file gate, two-million-character draft/request gate, 16k provider context and bounded history. |
| Logs/Audit | No source, selected text, prompt or AI response body in application/audit records. |

## Fixtures

- UTF-8 Markdown and LaTeX browser files.
- Invalid UTF-8 and binary PDF/DOCX files.
- Deterministic graph-chat provider response with captured request.
- Owner/researcher authoring draft and uploaded editable workspace.

## Commands

```text
cd apps/api && uv run ruff check app tests && uv run python -m pytest -q
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts
```

## Acceptance Evidence

- Backend Ruff passes; changed backend files pass Ruff format and all 289 backend tests pass.
- Four focused brainstorm API tests prove selection/history/source bounds, redaction, provider
  provenance, no tool calls and zero hidden chat/document/version persistence.
- Frontend ESLint, TypeScript, 88/88 Vitest cases and the 14-route production build pass.
- Nine Playwright cases pass across desktop/tablet/mobile. They prove local editable import before
  upload, explicit Send, non-mutating AI response, explicit Append, governed Create, post-upload
  brainstorm, existing selected-text proposal/Accept and zero horizontal overflow.
- The desktop E2E explicitly proves side-by-side editor/chat at 1920×1080 and no overflow at
  1366×768; live Chrome screenshot `/tmp/document-editor-chat-final-1920.png` confirms the layout.
- Rebuilt PostgreSQL/API/worker/frontend runtime is healthy on API `18000` / frontend `13000`.
- Fresh `harness-cli story complete US-DOCUMENT-UNIFIED-EDITOR-CHAT --json` reran the full command
  and passed; detailed implementation trace #43 meets the high-risk requirement at tier 3/3.
