# US-DISCORD-BOT-TEST-RUNBOOK Executable Discord Bot Test Runbook

## Status

implemented

## Lane

normal

## Product Contract

A repository operator can configure a least-privilege Discord test application, run the
implemented gateway against the local Research System, exercise its supported source and
failure paths, and prove receipt, relationship-graph and related knowledge-gap outcomes
without copying secrets into repository artifacts.

## Relevant Product Docs

- `Docs/Discord Bot Test Runbook.md`
- `apps/discord-bot/README.md`
- `Docs/Intake Occurrence and Receipt Specification.md`
- `Docs/Research System Completion Plan.md`

## Acceptance Criteria

- The runbook covers Discord application creation, Message Content intent, minimum
  permissions, application-command scope and guild/channel ID discovery.
- It creates a namespace-scoped service account with only `intake:submit` and
  `intake:read-own`, and includes revoke/secret handling instructions.
- It contains executable automated, local-stack and bot startup commands.
- It defines acceptance cases for article URLs, multiple links, duplicate delivery, PDF,
  Reel/partial sources, allowlists and slash commands.
- It shows how to prove the receipt, approved relationship-graph result and active related
  knowledge gaps.
- Expected reactions, review boundaries, troubleshooting and cleanup are explicit.

## Design Notes

- Commands: Compose, pytest, curl and optional jq only.
- Queries: receipt by Discord occurrence ref, relationship graph query and active gap list.
- API: `/api/v1/auth/service-accounts`, `/api/v1/intake/receipts`,
  `/api/v1/graph`, `/api/v1/gaps`, `/api/v1/ai/providers`.
- Domain rules: the gateway is an intake adapter; guarded approval remains API-owned;
  hierarchy placement stays governed; only related active gaps are disclosed.
- UI surfaces: `/ingestion`, `/graph`, `/graph/changes`.
- Non-goal: this docs story does not create a live Discord app, credentials or new runtime
  behavior.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Existing Discord gateway test suite passes |
| Integration | Existing Discord receipt-to-graph-and-gap backend proof passes |
| E2E | Operator checklist and live Discord cases are executable but require external credentials |
| Platform | Compose config validates and Discord image builds |
| Release | Not applicable to docs-only local test guidance |

## Harness Delta

No Harness behavior change. Intake 24 maps this normal-lane docs task to this story.

## Evidence

- `git diff --check` and Markdown fence checks pass.
- `docker compose config -q` passes.
- All 36 Discord gateway tests pass.
- `test_discord_receipt_auto_approves_into_graph_and_reports_related_gap` passes.
- `docker compose --profile discord build discord-bot` succeeds.
- Harness completion reran the static contract verifier and marked the story implemented.
- Live guild delivery remains an operator acceptance step because repository-safe validation
  cannot create or retain the owner's Discord credentials.
