# Session Log

## Context

- User request: Remove the mock provider.
- Agent: Codex.
- Date/time: 2026-07-17 00:22 +07.

## Work Done

- Files changed: `apps/api/app/core/config.py`, `apps/api/app/services/ai.py`, `apps/api/app/schemas/ingestion.py`, `apps/api/tests/conftest.py`, `apps/api/tests/test_ingestion.py`, `apps/web/components/intake/intake-form.tsx`, `apps/web/components/intake/submission-list.test.tsx`, `.env`, `.env.example`, `docker-compose.yml`, `README.md`, the MVP/completion/implementation docs, `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`, and this session log.
- Behavior changed: Removed the application AI mock factory and registry entry, made Mistral the configured default, rejected new `provider=mock` requests, selected only configured/reachable providers in the UI, and disabled submission when none is usable. Deterministic AI classification now exists only in backend tests.
- Commands run: Searched all mock references; inspected runtime provider/model availability without printing keys; ran Ruff, backend Pytest in an ephemeral Compose container, frontend ESLint/TypeScript/Vitest/production build, Compose config validation, Docker rebuild/recreate, HTTP/provider-registry checks, mock rejection probe, service status and startup log scan.

## Reasoning / Decisions

- Decision: Use Mistral as the running default because it is configured and previously verified; do not make the currently empty Ollama installation active.
- Reason: A real configured provider keeps intake functional while honoring the request to remove fake output. UI availability state is explicit when no provider can be used.
- Alternatives considered: Making Ollama the default was rejected for the current runtime because `ollama list` returned no models. Rewriting or deleting 13 historical mock-provenance rows was rejected because it would corrupt or remove accurate history; none of those rows is an active job.

## Verification

- Tests/checks: Ruff; 39 backend tests; frontend ESLint, TypeScript, 12 Vitest tests, Next.js build; Compose config; direct/proxied runtime health; `/ingestion`; `/ai/providers`; invalid mock intake; Compose status and recent error scan.
- Result: All checks pass. The live registry contains only `ollama`, `openai`, `deepseek`, `gemini`, `openrouter`, and `mistral`; Mistral is active/configured; `provider=mock` returns HTTP 422; all four core services are running and PostgreSQL is healthy; runtime logs are clean.

## Next Agent Notes

- Continue from: The project is running at `http://localhost:13000` with Mistral active.
- Watch out for: Historical completed intake rows still truthfully retain `provider_name=mock`; there are no active mock jobs. The graph module still has its separate contract-only `GRAPH_DATA_PROVIDER=mock`, which DEC-016 explicitly leaves unchanged.
- Suggested next command: `curl -sS http://localhost:13000/api/v1/ai/providers`.

## Known Issues

- The host `apps/api/.venv` has stale pre-monorepo interpreter paths, so direct host Pytest fails before collection. The full backend suite passes in an ephemeral Compose container.
- The current host Ollama model list is empty, so Ollama remains visible but unreachable/disabled until a configured model is installed and reachable.

## Next Best Action

- Obtain product-owner acceptance on the live no-mock Mistral intake selector, then continue with the already-planned intake receipt/attachment-storage specification.
