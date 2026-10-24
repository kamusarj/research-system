# Validation

## Proof Strategy

Use synthetic current/legacy HTML fixtures and an injected HTTP transport so tests never depend on
a live or retained third-party conversation. Inspect persisted rows, exact provider-double history,
safe audit payloads and the user-visible import/fork labels. A live public-share smoke may print
aggregate counts only and is supplementary, not the deterministic completion gate.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | URL allowlist; React loader decode; visible text/code extraction; hidden/raw-tool filtering; generated-image tool media; size/count/character/image-byte bounds; GFM/HTML safety; image-host allowlist. |
| Integration | Import endpoint persists ordered provenance/messages and local image references atomically; cached-image endpoint; typed fetch/parse/media errors; imported history reaches provider double without media URLs. |
| E2E | Researcher imports a link, sees rendered Markdown and same-origin cached image, imported/local labels and source link, then sends a local continuation; viewer cannot see the import mutation action. |
| Platform | SQLite migration upgrade/check/downgrade/upgrade; rebuilt API/frontend runtime health and route smoke. |
| Performance | HTML, message-count, total-character, image-count and image-byte caps are enforced before persistence. |
| Logs/Audit | Audit contains only aggregate/hash provenance; no URL, HTML or transcript. |

## Fixtures

- Synthetic React loader HTML with ordered user/assistant/system/tool records.
- Synthetic legacy `__NEXT_DATA__` share payload.
- Mock HTTP responses for redirect, private peer, non-HTML, oversized, deleted and challenge cases.
- Configured graph-chat provider double for local continuation.

## Commands

```text
cd apps/api && uv run ruff check app tests
cd apps/api && uv run python -m pytest tests/test_chatgpt_import.py tests/test_graph_chat.py tests/test_migrations.py
cd apps/web && npm run lint
cd apps/web && npx tsc --noEmit
cd apps/web && npm test -- --run
cd apps/web && npm run build
```

## Acceptance Evidence

- Backend importer coverage: `16/16` tests pass for exact URL allowlisting, current React loader,
  legacy payloads, visible-content filtering, generated-image tool media, transient asset retry,
  local cache/serving, redirect/size bounds, persistence/audit and local continuation history.
- Focused backend story verification: `32/32` importer, graph-chat and migration tests pass; Ruff
  passes across `app`, `tests` and `migrations`.
- Full backend regression: `280/280` tests pass. The only warning is the pre-existing
  FastAPI/Starlette TestClient `httpx` deprecation.
- Full frontend regression: TypeScript and ESLint pass, `80/80` Vitest tests pass, and the Next.js
  production build generates all 14 routes including `/chat`.
- Responsive browser proof: `6/6` Playwright cases pass across desktop, tablet and mobile for both
  existing governed chat and import → labelled snapshot → local continuation.
- Runtime proof: the existing PostgreSQL volume migrated transactionally to
  `f8b3d1e6a204 (head)`; database, API, worker and rebuilt frontend are running on the documented
  `18000/13000` override. A current public share produced 5 messages and one locally cached PNG;
  runtime import returned 201 and the same-origin media route returned the 2,475,962 bytes with 200.
- Harness intakes `#33-34`, accepted decisions `0022-0023`, implemented high-risk story
  `US-CHATGPT-SHARED-IMPORT` and its fresh verification command hold the durable completion proof.
