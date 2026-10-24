# Exec Plan

## Goal

Allow document-scoped AI chat to answer against bounded canonical document text.

## Scope

In scope:

- Canonical extracted document text in authorized document scope.
- Existing cloud redaction and total context limit.
- Deterministic tests proving inclusion, redaction and bounds.

Out of scope:

- Raw upload bytes, new providers, new tools, publication rights or retention changes.

## Risk Classification

Risk flags:

- External systems.
- Public/user-visible chat behavior.
- Existing provider-tested behavior.

Hard gates:

- External provider data boundary.

## Work Phases

1. Confirm accepted DEC-019 and plan boundaries.
2. Add canonical text to document scope with an inner bound.
3. Prove provider instructions include redacted text and never exceed the total bound.
4. Run focused and full backend proof.
5. Rebuild runtime and perform a non-provider live readiness check.
6. Update story/Harness/AI logs.

## Stop Conditions

Pause for human confirmation if:

- Raw file bytes would be required.
- Redaction or overall context bounds would need weakening.
- A new provider retention behavior is required.
- Any data migration or deletion appears.
