# Exec Plan

## Goal

Reduce invalid structured-output failures for document graph generation through one observable,
same-provider recovery attempt while preserving strict validation and reviewer control.

## Scope

In scope:

- Reproduce and classify the Mistral validation failure without exposing content or credentials.
- Add bounded recovery at the provider/application boundary best suited to schema failures.
- Add deterministic unit/integration coverage for success and terminal failure.
- Repeat a live Mistral document-graph run and record provider-safe evidence.

Out of scope:

- Cross-provider failover or automatic model selection.
- Prompt/schema redesign unrelated to the observed validation failure.
- Authentication/RBAC, storage, OCR/browser processing, projections or Discord.

## Risk Classification

Risk flags:

- External systems.
- Existing behavior.
- Audit/security.
- Weak proof before a live provider retry.

Hard gates:

- External provider behavior.
- Provider-safe observability.

## Work Phases

1. Reproduce and inspect the validation boundary.
2. Design the smallest bounded recovery path.
3. Add deterministic tests.
4. Implement without changing public contracts.
5. Run focused regression and live Mistral verification.
6. Update story, acceptance evidence, Harness trace and AI handoff logs.

## Stop Conditions

Pause for human confirmation if:

- The fix requires weakening validation or silently changing providers.
- A provider contract or public API shape must change.
- Reproduction would require exposing a credential or sensitive document content.
