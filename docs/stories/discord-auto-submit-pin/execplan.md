# Exec Plan

## Goal

Make zero-command link intake unambiguous and add a narrowly authorized Discord pin command.

## Scope

In scope:

- Preserve ordinary-message automatic intake.
- Mark `/submit` as optional in bot copy and docs.
- Add `/pin message_id:<id>` for the current allowlisted channel.
- Require resolved `PIN_MESSAGES` for caller and bot.
- Add typed bilingual success/refusal/error copy.
- Prove command registration, guild copying, authorization denial and successful pinning
  inside the production image.

Out of scope:

- Unpin, bulk pin, cross-channel fetch, graph pinning or new API scopes.

## Risk Classification

Risk flags:

- Authorization.
- Audit/security.
- External systems.
- Public contracts.
- Existing behavior.

Hard gates:

- Authorization and external Discord mutation.

## Work Phases

1. Record the corrected product contract and current Discord permission decision.
2. Add pure message-ID parsing and localized pin outcomes.
3. Register the pin command with allowlist/caller/app permission gates.
4. Pin only a fetched same-channel message with a bounded audit reason.
5. Extend unit and production-image command tests.
6. Update install/test documentation and Harness evidence.

## Stop Conditions

Pause for human confirmation if:

- “Pin” turns out to mean graph/UI pinning rather than a Discord channel pin.
- Cross-channel pinning or unpinning is requested.
- The service account or Research API would need additional authority.
- Validation would require a real owner token to claim repository completion.
