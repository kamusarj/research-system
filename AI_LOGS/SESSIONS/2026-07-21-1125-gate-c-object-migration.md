# Session Log

## Context

- User request: Set up and use Repository Harness, keep an active goal for completing the project,
  and continue from the state recorded in `AI_LOGS/`.
- Agent: Codex.
- Date/time: 2026-07-21 11:25 +07.

## Work Done

- Files changed:
  - Added `apps/api/app/services/object_migration.py`,
    `apps/api/tests/test_object_migration.py`, and
    `apps/api/scripts/verify_object_migration.py`.
  - Extended `apps/api/app/operations.py` with `migrate-objects` plan/execute/verify modes.
  - Added the `docs/stories/gate-c-object-migration/` story packet and
    `docs/decisions/0014-copy-verify-object-migration.md`.
  - Updated `README.md`, `Docs/Graph Intelligence v2 Operations Runbook.md`,
    `Docs/Research System Completion Plan.md`, `AI_LOGS/DECISIONS.md`,
    `AI_LOGS/TASKS.md`, and `AI_LOGS/HANDOFF.md`.
- Behavior changed:
  - Operators can obtain a read-only aggregate inventory of legacy local objects.
  - Execute requires an explicit copy-only confirmation and a completely clean inventory.
  - Each object is size/hash checked locally, copied to MinIO, read back and hash checked, locally
    rechecked, then committed with both database references and a bounded audit event.
  - Verify and repeated execute runs are resumable; the application never deletes the local source.
- Commands run:
  - `scripts/bootstrap-harness.sh`, Harness intake/story/decision/proof/trace commands.
  - Focused and full Ruff/Pytest verification plus `apps/api/scripts/verify_migrations.sh`.
  - `docker compose config --quiet`, API/worker image rebuild/recreate, health/readiness/log checks.
  - Real disposable-MinIO proof and a read-only plan against the main runtime.
  - Six document Playwright cases across desktop, tablet, and mobile.

## Reasoning / Decisions

- Decision: Use a copy-verify-reference-switch workflow with one database commit per object.
- Reason: It preserves recoverability, detects corrupt/missing metadata before copying, supports safe
  resume after interruption, and keeps PostgreSQL references authoritative without deleting source
  data.
- Alternatives considered: Bulk reference switching or automatic source deletion were rejected
  because either can leave widespread broken references and both make rollback less safe.

## Verification

- Tests/checks: Ruff; all 150 backend tests; SQLite migration parity; Compose validation;
  `git diff --check`; six Playwright document cases; direct/proxied health; graph readiness; recent
  service-log scan; real MinIO plan/execute/repeat/verify proof.
- Result: All checks passed. The disposable proof migrated and verified one 45-byte object, retained
  the local object, created one bounded audit event, and produced a repeat no-op. The main runtime
  plan is clean for 3 objects / 2,822 bytes, but execute was not run: PostgreSQL still has 3 plain
  keys, 0 remote keys and 0 migration audit events. The safe OpenAI provider probe remains a typed
  503 `CHAT_PROVIDER_UNAVAILABLE` external credential blocker.

## Known Issues

- A valid OpenAI runtime credential and product-owner Graph v2 acceptance remain external blockers.
- Production MinIO provisioning, backup, TLS/encryption policy and explicit migration execution are
  not authorized or completed.
- The first disposable-MinIO readiness poll ran before startup; retry succeeded and final proof was
  clean.

## Next Agent Notes

- Continue from: Specify the durable intake occurrence/receipt model before Discord; also recheck the
  OpenAI credential safely and run the acceptance checklist if external inputs become available.
- Watch out for: Never print credentials, never execute the production object migration without
  separate authorization, never delete the local volume, and do not touch `smart_exam_*`.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`.
