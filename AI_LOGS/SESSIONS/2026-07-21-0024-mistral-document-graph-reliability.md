# Mistral Document Graph Reliability

## Context

- User request: Continue the active project-completion goal after reading `AI_LOGS`, removing the
  remaining Mistral `AI_RESPONSE_INVALID` acceptance finding without using a mock or silent fallback.
- Agent: Codex.
- Date/time: 2026-07-21 00:24 +07.

## Work Done

- Files changed:
  - `apps/api/app/services/document_processing.py`
  - `apps/api/tests/test_documents.py`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `Docs/Graph Intelligence v2 Operations Runbook.md`
  - `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`
  - `docs/stories/document-provider-reliability/{overview,design,execplan,validation}.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - this session log
- Behavior changed: document-graph prompt v2 retries one Pydantic-invalid structured response with
  the same provider and a bounded graph-invariant checklist. It persists only a fully valid graph;
  a failed recovery retains the typed terminal error and explicit manual retry.
- Commands run: Harness bootstrap/intake/story/matrix; Ruff; focused and full Pytest; API/worker
  rebuild; live document upload/analyze/poll/graph/readiness; Playwright; Compose validation;
  focused diff check; service-log scan.

## Reasoning / Decisions

- Decision: retry only `ValidationError` once at the document-graph stage with the same provider.
- Reason: JSON Schema covers field shape, while graph-wide uniqueness/reference/self-loop invariants
  are enforced by Pydantic and can fail intermittently. This preserves selected-provider provenance,
  strict validation and the accepted separation between provider retry and durable job retry.
- Alternatives considered: silent cross-provider fallback was rejected because it hides provenance;
  partial graph persistence was rejected because it weakens invariants; repeating the durable job was
  rejected because it unnecessarily repeats extraction and paper-fit evaluation.

## Verification

- Tests/checks: Ruff; 88 backend tests; 27 Playwright desktop/tablet/mobile cases; Compose config;
  focused `git diff --check`; live Mistral workspace; readiness; log scan.
- Result: all checks pass. Live workspace `c91507a7-d186-418c-9202-34220ec75dfd` completed on its
  first structured response at score 74.5 with 20 supported nodes, 14 edges and zero dangling
  endpoints. The intermittent live failure did not recur, so actual recovery is proven by the
  deterministic invalid→valid test and terminal behavior by invalid→invalid.

## Known Issues

- The configured OpenAI credential is still rejected, so real graph chat and product-owner
  acceptance remain open.
- Product-owner checklist boxes remain intentionally unchecked.
- `apps/api/.venv/bin/pytest` has a stale shebang; `uv run --frozen python -m pytest` works.

## Next Agent Notes

- Continue from: replace the OpenAI runtime secret outside the repository, recreate API, and execute
  the prepared real scoped-chat acceptance path.
- Watch out for: never print or record provider keys; do not self-mark product-owner acceptance; use
  port overrides `API_PORT=18000 FRONTEND_PORT=13000` and do not touch `smart_exam_*` containers.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`.
