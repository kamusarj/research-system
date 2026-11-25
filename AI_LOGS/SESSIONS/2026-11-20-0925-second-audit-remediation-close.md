# Session Log — đóng US-SECOND-AUDIT-REMEDIATION

## Context

- User request: tiếp tục công việc dang dở (12 phát hiện audit lần hai).
- Agent: OpenCode (root đóng phiên); intake #21, `US-SECOND-AUDIT-REMEDIATION`, decision 0057.
- Date/time: 2026-11-20 09:25 +07.

## Files Changed

- `docs/stories/second-audit-remediation/validation.md`: ghi evidence hoàn tất.
- `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, session log này.
- Không sửa source code; toàn bộ fix đã nằm trong working tree từ các session 0901/0905/0907.

## Decisions and Behavior

- Ba nhóm worker trước đó đã sửa đủ 12 phát hiện (publication/evidence guards, research execution
  guards, guarded restore + worker secrets); phiên này chỉ xác minh, vận hành runtime và đóng.
- PostgreSQL smoke dùng DB tách biệt `baa_ci_lease_smoke_20261120` qua IP container
  (172.23.0.6, không map port host); drop ngay sau khi đo. Không đụng DB runtime cho test.
- Quiesce worker→api trước migrate (0 run running); api container tự chạy `alembic upgrade head`
  khi khởi động nên lease migration áp dụng đúng thứ tự fencing, không rolling mix binary cũ/mới.
- Backup timer cài lại qua `install_backup_timer.sh` để bản script ngoài repo nhận guard
  `.restore-*`; không chạy backup/restore thật chỉ để nghiệm thu. Restore verify-only là đủ bằng chứng.

## Commands / Verification

- Targeted regression (9 file test mới/sửa): **138 passed, 4 skipped** (SQLite).
- `verify_second_audit_remediation.sh` exit 0: API **920 passed, 4 skipped**; Discord bot 56;
  web 44 file/226 test; Ruff/ESLint/TypeScript/lock/shell/`git diff --check` đạt.
- `verify_postgres_migrations.sh` trên `baa_ci_lease_smoke_20261120`: upgrade `7d9f1b3c5e68`→
  `8e0a2c4d6f79`, check, downgrade -1, re-upgrade, check lại sạch.
- Guard + pgvector filter tests với `RESEARCH_LEASE_TEST_DATABASE_URL` trên PG đã migrate:
  **21 passed**.
- Runtime refresh: stop worker/api → start api (migrate) → healthy → start worker; smoke
  health 200, anonymous 401, worker log sạch. `alembic_version=8e0a2c4d6f79`, `lease_token` tồn tại.
- Backup timer active 02:30 (bản script mới có guard). Restore verify-only backup
  `20261120-084302-633536`: `{"mode": "verified", "objects": 4}`.
- `harness-cli story complete US-SECOND-AUDIT-REMEDIATION` = **pass**.

## Known Issues / Limits

- Starlette TestClient deprecation warning httpx; không ảnh hưởng proof.
- Fencing chỉ bảo vệ worker đã nâng bản; cần quiesce khi triển khai (đã làm ở runtime local).
- KPI paired eval vẫn bị chặn hạn mức Codex; Mistral generation bị tier/rate limit — proof riêng,
  không thuộc story này. Không hạ chuẩn bằng chứng.

## Next Best Action

Khi hạn mức Codex reset: chạy lại paired eval 8 câu cả 2 variant bằng
`~/.cache/business-ai-agents/audit-runtime/run-paired-eval-rerun.py` (corpus
`research-corpus-20261119.json`), sửa tiếp `AI_RESPONSE_INVALID` optimized nếu còn. Song song:
Linh quyết commit/push CI workflow; operator cài model thật nghiệm thu local models.
