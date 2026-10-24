# Session Log

## Context

- User request: Link messages must submit automatically without `/submit`; add a command
  that makes the bot pin a selected message.
- Agent: Codex
- Date/time: 2026-07-30 11:13 Asia/Bangkok
- Harness: owner correction intervention #5, intake #26, high-risk story
  `US-DISCORD-AUTO-SUBMIT-PIN`, decision `0018-discord-pin-authorization`.
- Harness trace: #33, detailed tier, meets the high-risk requirement.

## Work Done

- Files changed:
  - `apps/discord-bot/app/bot.py`
  - `apps/discord-bot/app/guidance.py`
  - `apps/discord-bot/app/pinning.py`
  - `apps/discord-bot/tests/test_gateway.py`
  - `apps/discord-bot/tests/test_guidance.py`
  - `apps/discord-bot/tests/test_pinning.py`
  - `apps/discord-bot/Dockerfile`
  - `apps/discord-bot/pyproject.toml`
  - `apps/discord-bot/README.md`
  - `scripts/verify_discord_bot_commands.sh`
  - `Docs/Discord Bot Test Runbook.md`
  - `Docs/Research System Completion Plan.md`
  - `README.md`
  - `docs/stories/discord-auto-submit-pin/*`
  - `docs/decisions/0018-discord-pin-authorization.md`
  - `AI_LOGS/DECISIONS.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - this session log
- Behavior changed:
  - Ordinary supported link/PDF messages remain and are now explicitly tested as the
    primary automatic intake path; `/submit` is labeled optional.
  - Added `/pin message_id:<id>` for a same-channel Discord pin.
  - Pin requires allowlist plus caller/app `PIN_MESSAGES`, validates the snowflake, treats
    existing pins idempotently and uses a bounded Discord audit reason.
  - Upgraded/bounded `discord.py` to `>=2.7.1,<3`.
- Commands run:
  - Harness bootstrap, high-risk intake/story/decision/intervention/verify/complete commands
  - Discord pytest, Ruff lint and Ruff format
  - Focused backend Discord receipt-to-graph-gap pytest
  - Compose validation and production image build
  - `scripts/verify_discord_bot_commands.sh`
  - Markdown fence, Bash syntax and diff checks

## Reasoning / Decisions

- Decision: interpret pin as a Discord channel pin and use `/pin message_id:<id>`.
- Reason: this matches the user's Discord-bot request while keeping the mutation target
  explicit.
- Decision: require current `PIN_MESSAGES` for caller and app rather than Manage Messages.
- Reason: Discord split the permission and requires Pin Messages after 2026-02-23.
- Decision: fetch through only `interaction.channel`.
- Reason: a supplied ID must not expand read/mutation scope across channels.
- Decision: retain `/submit` only as optional compatibility.
- Reason: ordinary `on_message` intake already provides the required zero-command path.
- Alternatives considered: auto-pin every source, allow any allowlisted user, cross-channel
  lookup and `/unpin`; rejected as broader than the request or authorization boundary.

## Verification

- Tests/checks:
  - 55 Discord gateway/guidance/pinning tests passed.
  - Ruff lint and format passed.
  - Focused backend receipt→guarded approval→graph→gap proof passed.
  - Compose config and decision verification passed.
  - Production image built with discord.py 2.7.1.
  - Actual callback smoke passed automatic plain-link intake, 7/7 commands, allowlist,
    caller/app permission denials, already-pinned idempotency and successful pin.
  - Harness high-risk story completion passed.
- Result: implementation and repository-safe proof complete.
- Known issues:
  - The first intervention command used unsupported source `user`; rerun with `human`.
  - The first expanded verifier used `followup.send_message` instead of discord.py's
    `followup.send`; the platform double was corrected and all paths pass.
  - A final read-only `rg` pattern used shell backticks and attempted the nonexistent
    `/submit` path; it changed nothing and was rerun with safe quoting.
  - Live guild mutation was not run because owner token and allowlist IDs were not supplied.

## Next Agent Notes

- Continue from: `Docs/Discord Bot Test Runbook.md`, TC-02 and TC-10.
- Watch out for: use **Pin Messages**, not only Manage Messages; do not grant Administrator.
- Suggested next command: `scripts/verify_discord_bot_commands.sh`
