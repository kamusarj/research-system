# Session: Discord auto-ingest and knowledge-gap alerts

## Context

- User request: inspect the Markdown plans for a Discord link-ingestion bot; if missing, plan and
  build one. A submitted article/Reel link should enter the system, run into the knowledge graph,
  and notify the Discord channel when a knowledge gap exists.
- Agent: Codex
- Date/time: 2026-07-30 09:54 +07

## Work Done

- Files changed:
  - `apps/discord-bot/app/{bot,config,gateway,messages}.py`
  - `apps/discord-bot/tests/test_gateway.py`
  - `apps/discord-bot/README.md`
  - `apps/api/app/schemas/intake_receipts.py`
  - `apps/api/app/services/{gaps,ingestion,intake_receipts}.py`
  - `apps/api/tests/{test_ingestion,test_intake_receipts,test_link_to_hierarchy}.py`
  - `.env.example`, `docker-compose.yml`, `README.md`
  - Relevant product docs, decision/story packet, and `AI_LOGS`.
- Behavior changed:
  - Confirmed that the Discord plan and gateway already existed.
  - Discord URL items now request guarded auto-approval by default through
    `DISCORD_AUTO_APPROVE_LINKS=true`.
  - Link approval refreshes persisted low-coverage gaps.
  - Receipt items expose at most ten active gaps related to their approved research tags.
  - Discord replies deduplicate and report at most five related gaps in English or Vietnamese.
  - Existing service-account scopes, partial-source review and canonical hierarchy governance are
    unchanged.
- Commands run:
  - `scripts/bootstrap-harness.sh`
  - Harness intake #23, decision `0017-discord-ingest-gap-alerts`, story
    `US-DISCORD-GAP-ALERTS`
  - Focused Pytest and `harness-cli story verify`
  - `make test`
  - `make lint`
  - `docker compose config -q`
  - `docker compose --profile discord build discord-bot`
  - Harness detailed trace #30, context score, and drift audit

## Reasoning / Decisions

- Decision: keep gap detection and filtering in the API; project only related active gaps through
  the already namespace-scoped receipt response.
- Reason: the Discord process remains a thin replaceable gateway with least privilege.
- Alternatives considered:
  - Direct `/gaps/detect` access or owner token in the bot: rejected as unnecessary privilege.
  - Automatic canonical hierarchy change-set apply: rejected because it weakens accepted graph
    governance; approved research already enters the relationship graph and the hierarchy proposal
    remains reviewable.
  - Automatic Reel media download/transcription: rejected by the accepted source-policy boundary.

## Verification

- Tests/checks:
  - Story proof: 45 backend and 36 Discord gateway tests.
  - Full regression: 252 backend, 36 gateway, 67 frontend tests.
  - Full Ruff/ESLint lint.
  - Compose configuration and Discord image build.
- Result: all commands passed. Two pre-existing non-failing Pytest warnings remain: Starlette
  `httpx` deprecation and the gateway environment's unknown `asyncio_mode` option.
  Harness trace #30 achieved detailed tier 3/3; drift audit entropy is `0/100`.

## Next Agent Notes

- Continue from: the code and `businessaiagents-discord-bot:latest` image are ready.
- Watch out for: no Compose stack was running during this session; no live database or Discord
  guild was mutated. A Reel without a user-supplied transcript remains partial by design.
- Suggested next command: after the owner provides managed tokens and allowlists, run
  `docker compose --profile discord up -d discord-bot` and inspect
  `docker compose logs -f discord-bot`.
