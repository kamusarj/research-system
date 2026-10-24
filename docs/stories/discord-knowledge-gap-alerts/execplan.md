# Exec Plan

## Goal

Complete the existing Discord intake path so eligible links automatically reach the
approved research/graph pipeline and relevant knowledge gaps are reported in the source
channel without moving research logic or elevated permissions into the bot.

## Scope

In scope:

- Guarded Discord auto-approval request configuration.
- Approval-triggered low-coverage gap refresh in the API.
- Related active gap summaries on scoped receipt reads.
- Bilingual gap alerts in the gateway reply.
- Focused backend and gateway regression proof plus docs/runtime configuration updates.

Out of scope:

- Automatic canonical ontology change-set approval/application.
- New database tables or migrations.
- Automatic Reel download/transcription.
- Real Discord deployment without owner-managed token and allowlist.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Existing behavior.
- Multi-domain.
- Weak proof around the combined workflow.

Hard gates:

- External Discord behavior.

Lane: high-risk. Intake: #23.

## Work Phases

1. Verify the existing Discord, receipt, approval, graph-change, and gap boundaries.
2. Record the bounded workflow decision.
3. Add deterministic API and gateway tests for auto-approval intent and related gap alerts.
4. Implement the smallest backend/gateway contract change.
5. Run focused tests, lint, Compose validation, and story verification.
6. Update product docs, Harness proof, and `AI_LOGS`.

## Stop Conditions

Pause for human confirmation if:

- Automatic canonical ontology publication becomes necessary.
- The bot would need a scope beyond `intake:submit` and `intake:read-own`.
- A schema migration or deletion becomes necessary.
- Existing source-access or human-review validation would need to be weakened.
