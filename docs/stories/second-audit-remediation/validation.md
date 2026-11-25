# Validation

## Proof Strategy

| Scope | Regression |
| --- | --- |
| Approved documents | Researcher403 trước side effect; owner vẫn sửa; version/restore/AIaccept |
| Evidence | Applied chat/document canonical provenance chặn xóa; draft-only vẫn xóa |
| Relations | Researcher không tạo cạnh published; draft và owner theo chính sách |
| Restore | Checksum/SQL/tar/smoke failure không resume; happy path; không đụng DB thật |
| Lease | Worker cũ về sau worker mới complete không ghi đè; heartbeat/cache/error paths |
| Verifier | Duplicate/conflicting verdict fail closed; cache2ngày phải miss |
| Report | Verified perspectives không bị báo thiếu evidence giả; không thêm fact |
| CPU | Adversarial3.5k+356char bounded comparisons; valid fuzzy fixtures giữ đúng |
| Search | type/tag/collection filters ở fallback và semantic fusion |
| Secrets/limiter | Compose worker nhận task keys; expired identities cleanup, active limits giữ nguyên |

## Evidence

Hoàn tất 2026-11-20. Từng nhóm có regression riêng (42 ca quyền/evidence/relations, 17 ca lease/verifier/
report/CPU, 31+7 ca restore/backup, 67 ca search/limiter/secrets) — tất cả đạt.

- Full proof `scripts/verify_second_audit_remediation.sh` exit 0: API **920 passed**, 4 skipped;
  Discord bot 56 passed; web 44 file/226 test; Ruff/ESLint/TypeScript/lock/shell/`git diff --check` đạt.
- PostgreSQL smoke: DB tách biệt `baa_ci_lease_smoke_20261120` — `verify_postgres_migrations.sh`
  đạt (upgrade `7d9f1b3c5e68`→`8e0a2c4d6f79`, check, downgrade, re-upgrade, check lại sạch); 21 test
  `test_research_execution_guards.py` + `test_pgvector_filter_contract.py` trên PG đã migrate đạt.
  Đã drop DB sau khi đo.
- Runtime: quiesce worker→api (0 run running), api khởi động chạy `alembic upgrade head` áp dụng lease
  migration (`alembic_version=8e0a2c4d6f79`, `lease_token` tồn tại), worker khởi động sau; health 200,
  anonymous 401, worker log sạch.
- Backup timer đã cài lại (`install_backup_timer.sh`) để bản script ngoài repo nhận guard `.restore-*`;
  timer active 02:30. Restore verify-only trên backup `20261120-084302-633536`: `mode=verified`,
  4 objects, không đụng dịch vụ thật.

Không dùng live model để thay unit proof; không thay artifact benchmark cũ hoặc kết luận KPI.
