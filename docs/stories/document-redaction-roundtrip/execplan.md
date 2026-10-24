# Exec Plan

## Goal

Keep sensitive local values byte-faithful across cloud AI edits and make resulting LaTeX failures
diagnosable without leaking source.

## Scope

In scope:

- Ephemeral reversible redaction tokens for document instant edits.
- Fail-closed marker validation.
- Safe XeLaTeX line/reason extraction.
- Backend, frontend and runtime regression proof.

Out of scope:

- Recovery of values already lost from the current local draft.
- Durable token maps or automatic patch application.

## Risk Classification

Risk flags:

- Audit/security and sensitive-data handling.
- External provider behavior.
- Existing edit and preview behavior.
- Multiple document AI/compiler surfaces.

Hard gates:

- Audit/security.
- External provider behavior.

## Work Phases

1. Capture placeholder leakage and compiler error fixtures.
2. Implement ephemeral tokenization/restoration and fail-closed validation.
3. Improve bounded compiler diagnostics.
4. Run full and live runtime proof.
5. Complete Harness and AI handoff evidence.

## Stop Conditions

Pause if the fix requires provider-visible originals, persistent token maps, source logging or
automatic mutation.
