# Validation

## Proof Strategy

Prove dry-run makes no changes; execute is impossible without explicit confirmation; invalid,
missing or mismatched local data blocks all copying; successful copies match local/remote size and
SHA-256 before database commit; both reference columns update together; audit payloads leak no keys;
repeat/interrupted runs converge; verify requires retained local parity; and no code path deletes a
local object.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Key classification, stream checksum, safe aggregate report and confirmation gate. |
| Integration | Plan/execute/verify, paired reference update, audit, mismatch refusal, repeat/resume. |
| E2E | Existing document upload/download/processing workspace remains green. |
| Platform | Main read-only plan; disposable real MinIO copy/read-back; image/secret configuration. |
| Performance | 64 KiB streaming and per-object commits; existing upload byte limit remains enforced. |
| Logs/Audit | Aggregate stdout and hashed-key audit only; no filenames, raw keys, bytes or secrets. |

## Fixtures

- Temporary local object root with valid, missing and mismatched files.
- SQLite attachment/workspace pairs and metadata-only attachment rows.
- Fake MinIO client for deterministic retry/commit tests.
- Disposable real MinIO server with no published host port and temporary application database.

## Commands

```text
cd apps/api && uv run ruff check app tests scripts
cd apps/api && uv run python -m pytest -q
bash apps/api/scripts/verify_migrations.sh
docker compose config --quiet
docker compose exec -T api python -m app.operations migrate-objects --mode plan
scripts/bin/harness-cli story verify US-GATEC-OBJECT-MIGRATION
```

## Acceptance Evidence

- Ruff and all 150 backend tests pass; nine focused migration tests cover read-only aggregate plan,
  copy/read-back/local checksum parity, paired reference updates, bounded audit payloads,
  confirmation enforcement, missing/size/hash/reference refusal, remote corruption, remote-native
  exclusion and repeat convergence.
- Migration parity passes at unchanged head `c5a8e2f4b901`; no schema change was needed. Base Compose
  validates and rebuilt API/worker images contain the command.
- The main runtime executed `plan` only: 3 referenced/legacy/eligible objects, 2,822 declared and
  verified bytes, zero missing/invalid objects and `clean=true`. No reference, audit row or object
  changed and no production migration was attempted.
- A disposable real MinIO server on the internal Docker network with tmpfs and no host port passed
  one copy, remote read-back, retained-local verification, transactional reference/audit update and
  a repeat run with zero additional migrations. The bounded result reported 45 verified bytes, one
  audit event and `deleted_objects=0`; the proof container was removed.
- Six document-upload/processed-workspace Playwright cases pass across desktop, tablet and mobile.
  Direct health and the rebuilt main runtime remain healthy on API 18000/frontend 13000.
