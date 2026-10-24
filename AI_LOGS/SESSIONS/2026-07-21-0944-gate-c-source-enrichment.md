# Session Log

## Context

- User request: Set up and explain Repository Harness, create a durable completion goal, inspect
  `AI_LOGS/`, and continue completing the project in the accepted order.
- Agent: Codex `/root`.
- Date/time: 2026-07-21 09:44 +0700.

## Work Done

- Files changed: added the high-risk Harness story packet under
  `docs/stories/gate-c-extraction/`, decision `docs/decisions/0011-bounded-source-enrichment.md`,
  migration `0b7d2e4f6a18`, OCR/browser services, transcript API/UI/tests, configuration and container
  wiring, operator/product docs, and the required `AI_LOGS` updates. Existing unrelated dirty files
  and all `smart_exam_*` services were preserved.
- Behavior changed: URL and uploaded scanned PDFs can use bounded in-memory PDFium/Tesseract OCR;
  JS-only articles can use an optional SSRF-guarded Browserless fallback; researchers can attach
  bounded timestamped transcripts to unpublished public Facebook Reel/video submissions without
  transcript text appearing in queue responses or audit logs. All three paths remain human-gated.
- Commands run: Harness bootstrap/intake/story/decision/trace/complete/audit commands; Ruff and full
  Pytest; Alembic empty upgrade/model parity/downgrade/upgrade; ESLint, TypeScript, Vitest, Next.js
  build and Playwright; Compose validation/build; real Tesseract and Browserless runtime probes;
  health/readiness/graph runtime checks; `git diff --check`.

## Reasoning / Decisions

- Decision: Keep OCR and browser rendering disabled by default, bounded and typed; use direct HTTP
  extraction before a single browser fallback; allow only user-supplied Reel transcripts.
- Reason: This adds practical source coverage without broadening the system into uncontrolled media
  scraping, silent publishing, unbounded browser access or sensitive audit replication.
- Alternatives considered: browser-render every URL, arbitrary browser egress, embedded OCR native
  bindings, automatic Reel download/transcription, and transcript bodies in audit events were
  rejected. See durable decision `0011-bounded-source-enrichment`.

## Verification

- Tests/checks: 125 backend tests; 15 Vitest files/28 tests; 30 local Playwright cases across
  desktop/tablet/mobile with six auth-only skips; migration round trip and model parity; web lint,
  typecheck and production build; API/worker/frontend image builds; base/browser Compose config;
  actual OCR and Browserless render smokes; live readiness and graph invariant checks.
- Result: all checks passed. Runtime is healthy on API `18000` and frontend `13000`, with 45 graph
  nodes and 32 edges valid. Harness story `US-GATEC-EXTRACTION` is implemented with detailed trace
  #10; audit has only the intentionally open product-acceptance story.

## Known Issues

- OpenAI still returns typed `503 CHAT_PROVIDER_UNAVAILABLE` through the application path; no change
  set or provider response ID was produced, so only a credential replacement can unblock real chat.
- Product-owner acceptance remains open and cannot be inferred from engineering evidence.
- Neo4j/Meilisearch/pgvector projection materiality and remaining production TLS/egress, secret
  rotation, object migration and telemetry-retention work remain open.
- Pulling Browserless exhausted Docker storage; 6.582 GB of rebuildable unused builder cache was
  pruned without removing images, volumes or product data. Root storage has about 2.6 GB free.

## Next Agent Notes

- Continue from: active high-risk story `US-GV2-ACCEPT`; the project completion goal remains active.
- Watch out for: do not store provider secrets in the repository/logs, do not mark product-owner
  acceptance, do not remove legacy local objects, and do not touch unrelated `smart_exam_*` state.
- Suggested next command: replace the OpenAI credential outside version control, recreate API/worker,
  then run the scoped chat section of `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`.
