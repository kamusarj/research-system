# Validation

## Proof Strategy

Use pure tests for auto-intake wording, command catalog, snowflake validation and localized
outcomes. Build the production image and invoke the actual app-command callback with
credential-free fake Discord interactions to prove caller denial, bot denial, already-pinned
idempotency and successful same-channel pinning. No real guild mutation is required for
repository completion.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Plain link is actionable; `/submit` marked optional; snowflake bounds; bilingual pin copy |
| Integration | Existing receipt and auto-intake gateway regression |
| E2E | Actual `/pin` callback denial/idempotent/success paths in production image |
| Platform | Seven commands register/copy to guild; Compose validates; image builds |
| Performance | One same-channel fetch and at most one pin call per command |
| Logs/Audit | Safe local action logs; bounded Discord audit reason; no message content/token |

## Fixtures

- Fake allowlisted guild `123` and channel `456`.
- Caller/app permissions with independent `pin_messages` booleans.
- Fake target message ID `789`, pinned and unpinned variants.

## Commands

```text
PYTHONPATH=apps/discord-bot apps/api/.venv/bin/python -m pytest apps/discord-bot/tests
apps/api/.venv/bin/ruff check apps/discord-bot/app apps/discord-bot/tests
apps/api/.venv/bin/ruff format --check apps/discord-bot/app apps/discord-bot/tests
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_ingestion.py::test_discord_receipt_auto_approves_into_graph_and_reports_related_gap
docker compose config -q
scripts/verify_discord_bot_commands.sh
```

## Acceptance Evidence

- 55 Discord gateway/guidance/pinning tests pass.
- Ruff lint and format checks pass.
- The focused backend Discord receipt → guarded auto-approval → relationship graph →
  related knowledge-gap proof passes.
- Compose config validates and the production image builds with `discord.py 2.7.1`.
- Production-image callback smoke proves:
  - an ordinary plain-link message reaches automatic collection without `/submit`;
  - all seven commands register and copy to the guild;
  - invalid ID and outside-allowlist requests do not fetch;
  - caller and bot `PIN_MESSAGES` denials do not fetch;
  - an already-pinned target causes no second mutation;
  - an authorized target receives one pin with a bounded actor audit reason.
- Decision `0018-discord-pin-authorization` static verification and Harness story
  completion pass.
- Live guild mutation remains owner acceptance because credentials are external.
