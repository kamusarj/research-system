# Gate C Routed MinIO Storage

## Context

- User request: Continue the active project-completion goal, first recheck OpenAI acceptance and then
  make concrete Gate C progress without weakening the accepted order or contracts.
- Agent: Codex.
- Date/time: 2026-07-21 00:41 +07.

## Work Done

- Files changed:
  - `apps/api/app/services/object_storage.py`
  - `apps/api/app/services/documents.py`
  - `apps/api/app/services/document_processing.py`
  - `apps/api/app/core/config.py`
  - `apps/api/tests/test_object_storage.py`
  - `apps/api/tests/test_documents.py`
  - `apps/api/pyproject.toml`, `apps/api/uv.lock`
  - `.env.example`, `docker-compose.yml`, `README.md`
  - `Docs/Research System Completion Plan.md`
  - `Docs/Research System Implementation Plan.md`
  - `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`
  - `docs/stories/gate-c-minio-storage/{overview,design,execplan,validation}.md`
  - `docs/decisions/0008-routed-object-storage.md`
  - `docs/stories/graph-intelligence-v2-acceptance/validation.md`
  - `AI_LOGS/DECISIONS.md`, `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`
  - this session log
- Behavior changed: optional MinIO writes return scheme-qualified opaque keys; reads/deletes route
  remote keys to MinIO and existing plain keys to local storage. Uploads remain size/hash bounded,
  downloads stream safely, buckets are pre-provisioned by default, safe storage 5xx failures retry
  through the bounded document worker policy, and local storage remains default.
- Commands run: Harness bootstrap/intake/story/decision/matrix; safe OpenAI application probe; SDK
  lock/sync; Ruff; focused/full Pytest; Docker image builds/recreate/restart; disposable MinIO live
  round trip; rebuilt local upload/download; Playwright; Compose/diff/log/health/readiness checks.

## Reasoning / Decisions

- Decision: plain keys permanently route to local storage and MinIO keys use
  `minio://<configured-bucket>/...`; backend selection changes only new writes.
- Reason: a global reinterpretation of existing keys would make historical objects unavailable and
  rollback unsafe. Opaque scheme routing avoids a destructive database/object migration.
- Alternatives considered: duplicate backend columns were deferred; silent global switching and
  automatic migration were rejected; bundling an outdated server image as production deployment was
  rejected. Managed MinIO provisioning, TLS/encryption, backup and secrets stay external.

## Verification

- Tests/checks: Ruff; 96 backend tests; 27 Playwright desktop/tablet/mobile cases; Compose config;
  focused diff check; final API/worker image build; direct/proxied health/readiness and clean logs.
- Result: all checks pass. Disposable internal MinIO passed put/open/delete and was removed. Rebuilt
  local workspace `32494694-4e0f-4b80-9086-3d78143672b5` downloaded exact bytes using a plain key.

## Known Issues

- OpenAI recheck session `651f826e-24d0-4341-bbdf-5aa3c5121056` still returns typed 503; real chat
  and product-owner acceptance remain open.
- Auth/RBAC needs a confirmed identity/session/role decision before implementation.
- Production MinIO provisioning, managed secrets, TLS/encryption, backup and a checksummed migration
  command remain separate Gate C work; the local object volume must be retained.
- Compose hit a stateless container rename race during simultaneous recreate; the old frontend
  container was removed, named volumes/PostgreSQL were preserved, and all services recovered.

## Next Agent Notes

- Continue from: obtain/verify the replacement OpenAI secret; otherwise specify auth/RBAC and managed
  secret deployment or the safe legacy-object migration tool.
- Watch out for: never print provider/storage credentials; do not remove the local object volume;
  do not self-mark product-owner acceptance; do not touch `smart_exam_*`.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`.
