# Session Log

## User request

Cho phép người dùng nhập API của riêng họ cho trò chuyện AI.

## Files changed

- API: `app/api/chat.py`, `app/core/localization.py`, `app/models.py`, `app/schemas/chat.py`,
  `app/services/graph_chat.py`, `app/services/providers/openai_graph_chat.py` under `apps/api`.
- `apps/api/migrations/versions/3e5f7a9b1c24_add_chat_credential_source.py`.
- `apps/api/tests/test_personal_chat_api.py`.
- Web: `app/chat/page.tsx`, `app/chat/page.test.tsx`, `app/globals.css`,
  `components/chat-api-settings.tsx`, `lib/api.ts`, `lib/chat.ts`, `lib/types.ts`,
  `e2e/personal-chat-api.spec.ts` under `apps/web`.
- `README.md`, `Docs/Research System Implementation Plan.md`,
  `Docs/Research System Architecture Design.md`.
- `docs/stories/personal-chat-api/{overview,design,execplan,validation}.md`.
- `docs/decisions/0046-ephemeral-personal-chat-api.md`.
- `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`, this session.
- Existing Harness database intake/story/decision/proof/trace records.

## Decisions made

- Default to ephemeral keys after asking optional retention preference and stating the assumption.
  No response was received before implementation; persistent encrypted account storage is not built.
- OpenAI and DeepSeek use existing fixed HTTPS endpoints and request-owned provider instances.
  Global settings are unchanged; API keys never enter model context or browser/server storage.
- Personal sessions require a key each turn before writing a message; no silent system fallback.
- React state is remounted when identity changes and removed on chat-page unmount.
- Provider and model metadata plus `credential_source` persist; model is pinned when creating.
- Team chat visibility, auth/CSRF, rate controls and human graph approval remain unchanged.
- Named ORM PaperEvaluation checks were aligned to existing migration/database names because
  the newer runtime Alembic detects unnamed metadata as removed constraints. No SQL check was removed.

## Commands/tests run

- Harness bootstrap, intake #8, story add/update/complete, decision add and detailed trace.
- `.venv/bin/ruff check app tests`; focused pytest personal/chat/import/auth/migrations.
- `.venv/bin/python -m pytest`: all 334 tests pass.
- `npm run typecheck`, `npm run lint`, focused Vitest chat/Markdown/app-shell: 14 tests pass.
- `E2E_BASE_URL=http://localhost:13001 npx playwright test e2e/personal-chat-api.spec.ts e2e/graph-chat.spec.ts`.
- `E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/personal-chat-api.spec.ts e2e/graph-chat.spec.ts`.
- `docker exec businessaiagents-api-1 python -m alembic upgrade head/check/current`.
- `docker restart businessaiagents-api-1`; `docker restart businessaiagents-frontend-1`.
- Frontend startup `npm run build`, HTTP health, Docker state/IDs, data counts and diff checks.

## Verification result

- API tests demonstrate distinct keys per caller/provider, pinned models, no global mutation,
  no persistence in SQLite dump or responses/logs, no key echo on invalid input/provider failure,
  no fallback/written turn without key, personal ChatGPT import, auth role and CSRF protection.
- Frontend tests demonstrate password masking, no browser storage writes, create/send credentials,
  key clearing on identity changes/unmount and explicit removal without deleting chat.
- 12/12 E2E pass across desktop/tablet/mobile on dev and production. AI calls are intercepted
  with synthetic credentials; no paid real-provider request is made by verification.
- Production build passes on 15 routes. API/frontend healthy at 18000/13000.
- SQLite full migration parity passes; PostgreSQL head is `3e5f7a9b1c24` and schema check is clean.
- Real data remains 10 sessions and 32 messages; all ten legacy sessions use `system`.
- Only API/frontend restarted. Worker/database/volumes and unrelated Smart Exam preserved.
- Initial test mistakes (503 failure envelope and snapshot fixture total_characters) were corrected.
- Direct `.venv/bin/pytest` full collection cannot resolve `tests` namespace in this restored
  workspace; invoking `.venv/bin/python -m pytest` resolves imports and all tests pass.
- Screenshot artifacts in `/tmp/personal-chat-settings-*.png` use masked synthetic keys only.

## Known issues

- Refresh/navigation/logout loses temporary keys by design; no encrypted account vault exists.
- Only OpenAI/DeepSeek graph chat is in scope; no arbitrary endpoints or worker/document BYOK.
- History is still shared within the team. A personal API key is not private conversation storage.
- Starlette emits an existing testclient deprecation warning; tests still pass.
- Disk space remains low (approximately 2.9 GB); no image/dependency rebuild or pruning performed.

## Next best action

Open `/chat` → API của tôi → choose provider/model and enter a real personal key in the UI.
Use API cá nhân when creating/importing; actual provider access is checked on the first sent turn.
