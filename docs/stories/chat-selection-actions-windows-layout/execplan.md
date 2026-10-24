# Exec Plan

## Goal

Make selected-text actions discoverable in both document and chat workflows and give Brainstorm
chat a focused layout that fits Windows desktop/laptop viewports.

## Scope

In scope:

- Selection popover behavior and accessibility.
- Document proposal action placement.
- Chat composer shortcuts that require explicit Send.
- Removal of redundant chat right-rail UI and responsive overflow fixes.
- Unit, responsive E2E, build and live-browser proof.

Out of scope:

- Backend, schema, provider or audit changes.
- Historical chat mutation.
- Automatic chat submission.

## Risk Classification

Risk flags:

- Public product behavior, cross-platform layout, existing behavior, two product domains and a
  previously weak real-selection proof.

Hard gates:

- None; no external provider behavior or durable data contract changes.

## Work Phases

1. Record intake, story and selection-safety decision.
2. Build selection anchor utilities and contextual popovers.
3. Simplify chat information architecture and Windows viewport sizing.
4. Add unit and real browser selection tests.
5. Rebuild runtime and verify desktop/tablet/mobile overflow.
6. Update product docs, Harness proof/trace and AI handoff logs.

## Stop Conditions

Pause if the change would auto-send chat content, mutate imported/history messages, remove graph
proposal review access or require a new backend contract.

