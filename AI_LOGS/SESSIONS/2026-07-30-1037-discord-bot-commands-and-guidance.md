# Session Log

## Context

- User request: Thêm command, hướng dẫn và trải nghiệm sử dụng như bot Discord thông thường.
- Agent: Codex
- Date/time: 2026-07-30 10:37 Asia/Bangkok
- Harness: intake #25, story `US-DISCORD-BOT-COMMAND-GUIDE`, normal lane.
- Harness trace: #32, standard tier, meets the normal-lane requirement.

## Work Done

- Files changed:
  - `apps/discord-bot/app/bot.py`
  - `apps/discord-bot/app/guidance.py`
  - `apps/discord-bot/app/messages.py`
  - `apps/discord-bot/tests/test_guidance.py`
  - `apps/discord-bot/README.md`
  - `Docs/Discord Bot Test Runbook.md`
  - `Docs/Research System Completion Plan.md`
  - `scripts/verify_discord_bot_commands.sh`
  - `docs/stories/discord-bot-command-guide.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - this session log
- Behavior changed:
  - Added `/help`, `/guide`, `/sources` and `/ping` beside `/submit` and `/status`.
  - Added localized presence, mention guidance and safe application-command error handling.
  - Corrected guild sync by copying registered global commands into each configured guild
    before `sync`.
  - Kept every command allowlist-gated and added no API/service-account permission.
- Commands run:
  - `scripts/bootstrap-harness.sh`
  - Harness intake/story add, update, verify and complete commands
  - Discord pytest and Ruff commands
  - `docker compose config -q`
  - `scripts/verify_discord_bot_commands.sh`
  - Markdown fence, `bash -n` and `git diff --check`

## Reasoning / Decisions

- Decision: use modern slash commands rather than introduce a second prefix-command parser.
- Reason: the existing gateway already used Discord application commands and the requested
  discoverability can remain in one permissioned command surface.
- Decision: keep guidance content in a Discord-independent module.
- Reason: command catalog, bilingual fallback and reply limits can be tested without a guild
  or network.
- Decision: informational commands make no Research API request and remain allowlist-gated.
- Reason: help must not expand the existing `intake:submit` / `intake:read-own` boundary.
- Decision: add a production-image command-tree smoke.
- Reason: the local API virtualenv intentionally lacks `discord.py`; pure unit tests alone
  cannot prove actual `CommandTree` registration and guild copying.

## Verification

- Tests/checks:
  - 43 Discord gateway/guidance tests passed.
  - Ruff passed.
  - Compose config passed.
  - Production Discord image built.
  - Command-tree smoke reported 6/6 commands registered and copied into the guild tree.
  - Markdown fences, Bash syntax and diff whitespace passed.
  - Harness story completion passed.
- Result: implementation and repository-safe proof complete.
- Known issues:
  - First verifier attempt used `docker compose images -q`, which returns only images attached
    to created containers in this Compose version. The verifier now derives the built image
    name from Compose JSON config and passes.
  - `shellcheck` is not installed; `bash -n` and successful end-to-end script execution pass.
  - Live guild rendering was not run because no owner token or allowlist IDs were supplied.

## Next Agent Notes

- Continue from: `Docs/Discord Bot Test Runbook.md`, Gate 4 and TC-08/TC-09, once owner
  credentials are available.
- Watch out for: keep new commands inside the allowlist boundary and keep graph/gap
  mutations out of the Discord service account.
- Suggested next command: `scripts/verify_discord_bot_commands.sh`
