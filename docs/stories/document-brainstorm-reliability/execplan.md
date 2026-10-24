# Exec Plan

## Goal

Make a timed-out Document Brainstorm request recoverable without losing the user's question or
exposing an internal DeepSeek error.

## Scope

In scope:

- Typed frontend classification of brainstorm API and transport failures.
- Localized timeout/rate-limit/invalid-response feedback.
- One explicit, user-triggered Retry of the same question and pre-request history.
- Unit/component and live runtime proof.

Out of scope:

- Automatic retries or provider fallback.
- Provider timeout or model changes.
- Persistence of pre-create brainstorm history.

## Risk Classification

Risk flags:

- External systems.
- Existing behavior.
- Public user-visible behavior.
- Weak timeout-recovery proof in the existing story.

Hard gates:

- External provider behavior.

## Work Phases

1. Correlate browser report with API/provider telemetry.
2. Define safe retry and error-copy behavior.
3. Add deterministic component coverage.
4. Implement the smallest frontend change.
5. Run frontend, backend regression and live runtime checks.
6. Record Harness proof and handoff.

## Stop Conditions

Pause for human confirmation if the fix would require automatic paid retries, provider switching,
weaker document-mutation controls or a longer wait than the accepted provider deadline.
