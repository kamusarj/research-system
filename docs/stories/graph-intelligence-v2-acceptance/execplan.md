# Exec Plan

## Goal

Produce current, secret-safe evidence for the complete Graph Intelligence v2 product-owner
walkthrough and isolate any remaining external or human decision blocker.

## Scope

In scope:

- Core Compose service restart with preserved volumes.
- Health, feature, readiness, migration and invariant checks.
- Safe selected-provider credential/access verification through application behavior.
- Real upload, isolated graph, change review and scoped-chat walkthrough.
- Responsive UI, typed provider failure and rate-limit wording evidence.
- Harness trace and AI handoff updates.

Out of scope:

- Secret creation, rotation or storage outside the existing runtime mechanism.
- Product-owner approval on Linh's behalf.
- Gate C implementation, projection upgrades and Discord.

## Risk Classification

Risk flags:

- External systems.
- Existing behavior.
- Audit/security.
- Weak proof until the live walkthrough is repeated.

Hard gates:

- External provider behavior.
- Credential handling and audit/security.

## Work Phases

1. Discover current runtime and persisted state.
2. Start the bounded local stack and verify readiness.
3. Verify the configured DeepSeek default without exposing secrets; retain explicit OpenAI proof.
4. Execute non-chat and chat walkthrough paths.
5. Verify UI, errors, timing and logs.
6. Run the executable acceptance verifier, which requires both provider access and Linh's recorded
   checklist decision.
7. Record evidence, blockers and Harness/AI handoff state.

## Stop Conditions

Pause for human confirmation if:

- A valid replacement credential must be supplied or rotated.
- Product-owner wording/usability acceptance is required.
- The walkthrough would delete, overwrite or broadly mutate canonical data.
- Existing behavior contradicts the accepted Graph Intelligence v2 plan.
