# Session: Restore Document AI Provider Runtime

## Context

- User request: investigate why Document AI reported "The AI connection was interrupted. Your
  text is safe; try again."
- Agent: Codex
- Date/time: 2026-08-04 14:59 Asia/Bangkok

## Work Done

- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log only.
- Behavior changed: recreated the API and worker containers from the existing current `.env`, so
  the configured DeepSeek credential is now present in runtime again.
- Commands run: inspected recent API/frontend logs and provider status; compared only credential
  presence/length without printing secrets; recreated API/worker with the documented 18000/13000
  host-port override; called health, provider status and the real instant-edit endpoint through the
  frontend proxy; scanned fresh logs; ran `git diff --check`.

## Reasoning / Decisions

- Decision: repair runtime configuration only; do not change AI editing or proxy code.
- Reason: failed requests returned HTTP 503 in 0.3-1.3 ms and provider telemetry identified
  DeepSeek errors. The live API container lacked the key although current Compose configuration
  had it. This excludes the 125-second frontend proxy budget and the LaTeX compiler as causes.
- Alternatives considered: changing the default provider or increasing timeouts was unnecessary
  and would hide the stale-container cause.

## Verification

- Tests/checks: API `/health`; `/ai/providers`; one real DeepSeek document rewrite through
  `http://localhost:13000/api/v1/documents/edit-in-place`; recent API/frontend/worker log scan;
  `git diff --check`.
- Result: health returned `ok`; DeepSeek reports configured and chat-active; the real rewrite
  returned HTTP 200 in 9.9 seconds with replacement text and `auto_apply_allowed=false`; fresh logs
  show provider success and no proxy reset, traceback or server error.

## Next Agent Notes

- Continue from: runtime is healthy on API 18000 and frontend 13000.
- Watch out for: recreating API/worker with an older or incomplete environment can make provider
  selection and credential availability diverge again. Never record key values in logs.
- Suggested next command: `docker compose logs --since=10m api frontend | rg
  'document-instant-edit|edit-in-place|ERROR|Traceback'` if the UI reports another provider error.
