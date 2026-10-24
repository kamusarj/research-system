# Graph Intelligence v2 Product Acceptance

## Current Behavior

Graph Intelligence v2 engineering gates pass and the local Compose stack is healthy at the current
receipt migration head. The configured OpenAI credential remains rejected, but intake #14 and
decision 0016 authorize the already configured DeepSeek provider for the remaining graph-chat
walkthrough. The product-owner walkthrough remains unchecked in
`Docs/Graph Intelligence v2 Product Acceptance Checklist.md`.

## Target Behavior

The four-service local stack is healthy on the documented ports, the selected graph-chat provider is
verified without exposing credentials, and the upload, isolated graph, change review, scoped chat,
responsive UI and typed-error walkthrough has current evidence. DeepSeek is the temporary default;
OpenAI remains a reversible configuration choice. Only Linh records the final product-owner decision.

## Affected Users

- Product owner reviewing Graph Intelligence v2 for rollout.
- Local operator responsible for provider secrets and service health.

## Affected Product Docs

- `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`
- `Docs/Graph Intelligence v2 Operations Runbook.md`
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`

## Non-Goals

- Do not replace or print any provider credential from repository automation.
- Do not use the provider preflight as continuous health monitoring; it is an explicit real API call.
- Do not self-approve subjective product-owner checklist items.
- Do not implement Gate C, projection upgrades or Discord in this acceptance story.
- Do not modify or stop unrelated `smart_exam_*` containers.
