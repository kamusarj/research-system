# Repository Agent Instructions

This repository uses `AI_LOGS/` as the cross-agent handoff system. These instructions apply to all AI coding agents working in this repo, including Codex, Claude Code, OpenCode, Antigravity-style agents, and any other assistant with filesystem access.

## Required Startup Protocol

Before making any change, every agent must read these files in order:

1. `AI_LOGS/HANDOFF.md`
2. `AI_LOGS/TASKS.md`
3. `AI_LOGS/DECISIONS.md`
4. Any relevant docs under `Docs/`

If the user asks for implementation, check the current task state first. Do not assume the latest chat history is complete.

## Required Shutdown Protocol

Before ending a meaningful work session, every agent must update:

1. `AI_LOGS/HANDOFF.md`
2. `AI_LOGS/TASKS.md`
3. A new session log under `AI_LOGS/SESSIONS/`

Use this filename format for session logs:

```text
YYYY-MM-DD-HHMM-short-summary.md
```

The session log must include:

- User request
- Files changed
- Decisions made
- Commands/tests run
- Verification result
- Known issues
- Next best action

Use `AI_LOGS/TEMPLATES/session-template.md` if unsure.

## Safety Rules

- Never store secrets, tokens, API keys, credentials, customer PII, or sensitive business data in `AI_LOGS/`.
- Never revert user changes unless the user explicitly asks.
- Never overwrite planning docs without reading them first.
- If a task is ambiguous, inspect relevant docs and logs before asking the user.
- Keep implementation aligned with `Docs/Research System Implementation Plan.md`.

## Current Project Direction

The current accepted direction is:

- Local-first Research System MVP.
- Prioritize Research Knowledge Base before full collector/training automation.
- Start with docs/spec and only implement code when explicitly requested.
- Keep architecture upgradeable toward FastAPI, Next.js, PostgreSQL + pgvector, Neo4j, Meilisearch, Redis, MinIO, and Ollama.
- Use Markdown AI handoff logs before adding database/API-backed agent logs.

## Implementation Order

When implementation is requested, follow this order unless the user changes priority:

1. Local foundation.
2. Research CRUD.
3. Research frontend library/editor.
4. Search.
5. Graph projection.
6. AI enrichment.
7. RSS collector MVP.
8. Training Data Hub foundation.
9. Tests and docs polish.

## Verification Expectations

For docs-only changes:

- Check Markdown structure and code fences when practical.
- Update `AI_LOGS` if the session changed project state.

For code changes:

- Run the smallest relevant tests/checks.
- Record commands and results in the session log.
- If tests cannot run, record why in both final response and `AI_LOGS/HANDOFF.md`.

