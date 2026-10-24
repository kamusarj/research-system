# Exec Plan

## Goal

Prevent the frontend proxy from converting an observed long successful document edit into a false
connection failure.

## Scope

In scope:

- Bounded proxy budget correction and deployment override.
- Config/unit/build/Compose/runtime proof.
- Correlation against the captured 131.115-second API success.

Out of scope:

- Provider retries, streaming, background execution or schema changes.

## Risk Classification

Risk flags:

- External provider behavior.
- Existing user-visible workflow.
- Deployment/runtime configuration.

Hard gates:

- External provider behavior.

## Work Phases

1. Correlate frontend and API logs.
2. Correct and expose the bounded proxy budget.
3. Add configuration regression proof.
4. Recreate frontend and verify effective runtime.
5. Complete Harness and AI handoff evidence.

## Stop Conditions

Pause if the correction requires automatic paid retries, an unlimited connection, or a new
persistence boundary.
