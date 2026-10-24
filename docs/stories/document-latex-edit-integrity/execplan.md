# Exec Plan

## Goal

Prevent a rename or other whole-source AI edit from replacing valid LaTeX Raw source with provider
explanation text.

## Scope

In scope:

- Standalone LaTeX structure detection.
- Backend prompt and output enforcement for complete-source edits.
- Browser defense-in-depth before pending review.
- Regression tests using the reported explanatory response shape and a valid renamed document.

Out of scope:

- New API fields, persistence or automatic local mutation.
- General semantic verification of every free-form instruction.
- Multi-file LaTeX projects.

## Risk Classification

Risk flags:

- External provider behavior.
- Existing user-visible document editing behavior.
- Weak proof for malformed whole-source LaTeX replacements.

Hard gates:

- External provider output.

## Work Phases

1. Capture the reported malformed replacement as a deterministic regression fixture.
2. Add one shared structural rule in backend and an equivalent browser boundary check.
3. Strengthen the provider output contract for existing standalone source.
4. Run focused backend/frontend proof and full relevant checks.
5. Rebuild runtime and verify the live rename workflow when available.
6. Update Harness and AI handoff evidence.

## Stop Conditions

Pause if the fix requires automatic acceptance, source persistence, a weaker review contract or a
new provider call.
