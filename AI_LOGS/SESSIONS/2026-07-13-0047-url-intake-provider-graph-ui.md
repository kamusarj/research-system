# Session Log

## Context

- User request: hoàn thiện Research System trước Discord bot, hỗ trợ local/cloud AI providers, nghiên cứu/nâng cấp Knowledge Graph và tối ưu UI song ngữ Anh–Việt.
- Agent: Codex.
- Date/time: 2026-07-13 00:47 +07.

## Work Done

- Files changed: completion plan; AI settings/provider service; link-intake model/schema/service/API/migration/tests; typed graph service/API; bilingual context/shell/dashboard/intake/graph UI; CSS; Compose/env/docs and AI logs.
- Behavior changed: URLs can be submitted from manual/API/Discord-labelled sources, safely fetched, deduplicated, classified with one of six providers, reviewed and published into research/typed graph. Graph now renders as an interactive Cytoscape network. Locale EN/VI persists for shell and primary flows.
- Commands run: required AI log/docs reads; official provider/Neo4j/Cytoscape/i18n research; OpenAI Docs MCP registration; pytest/Ruff/ESLint/typecheck/Next build; npm install/audit; SQLite and PostgreSQL Alembic checks; Compose config and HTTP smoke checks.

## Reasoning / Decisions

- Decision: complete the source-neutral core before Discord and use one validated structured classification schema across provider-specific transports.
- Reason: avoids embedding business logic in the bot, keeps model choice configurable and makes graph projection deterministic/idempotent.
- Alternatives considered: treating all providers as OpenAI Chat Completions was rejected because OpenAI's current primary path is Responses structured output and Gemini/Ollama have native transports; adding Neo4j as source of truth was rejected.

## Verification

- Tests/checks: 12 backend tests; Ruff, ESLint and TypeScript pass; Next production build pass with `/ingestion` and Cytoscape `/graph`; npm audit 0 vulnerabilities; migration upgrade/downgrade/upgrade pass on SQLite and upgrade pass on PostgreSQL; Docker provider/graph APIs and pages HTTP 200.
- Result: all final checks pass. Existing Starlette TestClient deprecation warning remains. Initial Docker curls raced frontend restart but passed after readiness; historical module-not-found logs preceded installing Cytoscape into the named node_modules volume.

## Next Agent Notes

- Continue from: visually review `http://localhost:13000/ingestion` and `/graph`, then translate every remaining secondary workflow.
- Watch out for: HTML/plain-text extraction is synchronous and intentionally limited; cloud provider calls require environment keys and have not been live-tested because no credentials were supplied. Restart Codex before using the newly registered OpenAI Docs MCP in a later session.
- Suggested next command: `make test && make lint && make build`.
