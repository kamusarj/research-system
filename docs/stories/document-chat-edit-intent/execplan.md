# Exec Plan

## Goal

Make direct edit commands in contextual document chat create reviewed source patches rather than
advisory prose.

## Scope

In scope:

- Deterministic Vietnamese/English imperative detection.
- Routing to the existing custom instant-edit request.
- Selection-first and bounded whole-source targeting.
- Full diff plus Accept/Reject using the existing conflict-safe UI.
- Authoring and uploaded-editor tests, live browser and real-provider proof.

Out of scope:

- Automatic apply/save/index/publish.
- A new backend endpoint or data model.
- Unbounded whole-document edits.

## Risk Classification

Risk flags:

- External provider behavior.
- Existing behavior.
- Public user-visible workflow.
- Multiple document AI surfaces.

Hard gates:

- External provider behavior.

## Work Phases

1. Confirm current chat and instant-edit boundaries.
2. Specify deterministic routing and fail-closed size behavior.
3. Implement shared chat routing into existing hook callbacks.
4. Add original/proposed/accept/reject regression proof.
5. Rebuild and validate live behavior.
6. Complete Harness evidence and handoff.

## Stop Conditions

Pause if implementation requires automatic mutation, a new persistence boundary, weaker range
validation or a second provider call solely for intent classification.
