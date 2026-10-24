# Validation

## Proof Strategy

Use deterministic SQLite unit/API/concurrency/storage tests, migration parity and explicit backfill
fixtures, then apply the additive migration to a backed-up PostgreSQL runtime and prove counts,
references and unchanged processing/review/research state. Run current frontend/manual-intake E2E
and scan audit/log output for raw values.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Key derivation, metadata bounds, item status aggregation, bearer hashing/scopes. |
| Integration | Replay, repeated occurrence, multi-URL, concurrency, backfill, legacy dual-write. |
| E2E | Existing manual intake desktop/tablet/mobile plus fake source-neutral adapter contract. |
| Platform | Local and routed MinIO document durability; rebuilt PostgreSQL runtime. |
| Performance | Bounded item count and one canonical job under concurrent replay. |
| Logs/Audit | No token, raw occurrence ref, URL, filename or body in audit/log proof. |

## Fixtures

- Same occurrence/URL twice and concurrently.
- Different occurrences sharing one normalized URL.
- One receipt with multiple URLs.
- Same document ref/hash replay and ref/hash conflict.
- Same document bytes in different occurrences.
- Legacy source refs shared/null; failed/completed/reviewed jobs.
- Owner, researcher/viewer and two namespace-scoped service accounts.

## Commands

```text
cd apps/api
uv run --frozen ruff check app tests
uv run --frozen python -m pytest -q
uv run --frozen python scripts/verify_intake_receipt_migration.py
bash scripts/verify_migrations.sh
cd ../..
docker compose config --quiet
```

## Acceptance Evidence

- API/model/service-account, replay, namespace-isolation, compatibility and real concurrent-delivery
  coverage: `apps/api/tests/test_intake_receipts.py`.
- Additive migration/parity and legacy-state proof:
  `apps/api/scripts/verify_intake_receipt_migration.py` and `scripts/verify_migrations.sh`.
- Routed object-store proof against disposable real MinIO:
  `apps/api/scripts/verify_intake_receipt_minio.py` (`INTAKE_RECEIPT_MINIO_OK`).
- Local PostgreSQL rollout used a validated pre-migration dump and restore drill; post-migration
  counts were 27 receipts / 27 items / 27 links with zero missing references and an unchanged
  processing/review/research state hash.
- Manual-intake desktop/tablet/mobile E2E passed in the final regression run: 30 Playwright cases
  passed and six auth-only cases skipped as expected with trusted-local auth disabled.
