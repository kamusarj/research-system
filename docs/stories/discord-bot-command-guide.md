# US-DISCORD-BOT-COMMAND-GUIDE Discord Bot Commands and Guidance

## Status

implemented

## Lane

normal

## Product Contract

People in an allowlisted Discord channel can discover what the Research System bot does,
learn which sources and limits it supports, check that the gateway is responsive, submit a
source and inspect an earlier receipt through normal slash commands. Mentioning the bot
without a source points people to the guide. Informational commands do not expand the bot's
service-account scopes or graph authority.

## Relevant Product Docs

- `apps/discord-bot/README.md`
- `Docs/Discord Bot Test Runbook.md`
- `Docs/Research System Completion Plan.md`
- `Docs/Intake Occurrence and Receipt Specification.md`

## Acceptance Criteria

- `/help` lists every public command, automatic-message behavior and outcome reactions.
- `/guide` provides a short article/PDF-to-graph workflow and explains review/gap behavior.
- `/sources` names the supported source categories, public-access boundary and message/file limits.
- `/ping` gives an ephemeral gateway/latency response without calling a privileged API.
- Existing `/submit` and `/status` continue to work and every command remains allowlist-gated.
- Guild command synchronization includes the registered global command set.
- The bot presence and mention-without-source response make `/help` discoverable.
- Vietnamese and English copy have tested fallbacks and stay below Discord reply limits.

## Design Notes

- Commands: `/help`, `/guide`, `/sources`, `/ping`, `/submit`, `/status`.
- API: unchanged; informational commands make no API call.
- Tables: none.
- Domain rules: Discord remains a thin intake adapter; service-account scopes remain
  `intake:submit` and `intake:read-own`; graph publication and gap management remain API-owned.
- Discord surfaces: ephemeral informational replies, bot presence, slash-command descriptions.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Pure bilingual command copy, fallback, limits and command catalog tests |
| Integration | Existing receipt/gateway tests remain green |
| E2E | `scripts/verify_discord_bot_commands.sh` confirms all six commands register and copy to a guild |
| Platform | Compose validates and the Discord image builds |
| Release | Live guild execution remains owner-operated because it requires external credentials |

## Harness Delta

No Harness behavior change. Intake 25 maps this normal-lane product refinement to this story.

## Evidence

- 43 Discord gateway/guidance tests pass.
- Ruff passes for all Discord bot application and test modules.
- Compose config validates.
- `scripts/verify_discord_bot_commands.sh` builds the production image and proves all six
  commands register globally and copy into the configured guild command tree.
- Markdown fence, Bash syntax and repository diff checks pass.
- Harness completion reran the full verifier and marked the story implemented.
- Live rendering in a real guild remains owner-operated because Discord credentials are
  external and must not be stored in repository proof.
