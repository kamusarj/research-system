# Session Log

## Context

- User request: bắt đầu sửa các phát hiện audit lần hai.
- Agent: Codex `/root/fix_release`; intake #21, `US-SECOND-AUDIT-REMEDIATION`, decision0057.
- Date/time: 2026-11-20 09:07 +07.

## Files Changed

- `scripts/restore_local.py`, `scripts/backup_local.py`, `scripts/team.sh`, `Makefile`.
- `docker-compose.secrets.example.yml`, `Docs/Team Deployment Runbook.md`.
- `apps/api/tests/test_restore_local.py`, `apps/api/tests/test_backup_retention.py`,
  `apps/api/tests/test_worker_secrets.py`.

## Decisions and Behavior

- Restore mặc định chỉ xác minh; `--apply`/`RESTORE_APPLY=1` mới là lệnh bảo trì ghi đè.
- Kiểm manifest của engine, SHA-256/kích thước, archive path/link/type/trùng lặp, catalogue và
  dung lượng staging trước khi dừng ứng dụng. Không bắt buộc tạo cấu hình team để kiểm bản local.
- Restore dùng cùng Compose selection và project lock với backup. Giữ lock đến sau thao tác dừng
  an toàn khi lỗi. Luồng apply: quiesce → stage objects → PostgreSQL single transaction → promote
  objects → migration/parity → object/hash/graph smoke → resume đúng các dịch vụ trước đó → live
  health/auth smoke → dọn tệp cũ.
- Tệp cũ được giữ đến sau live smoke. Bất kỳ lỗi nào sau bảo trì đều cố dừng các dịch vụ và trả lỗi
  theo bước; không có auto-resume trong finally. Không tuyên bố transaction chung database/tệp.
- Runbook bỏ recipe restore rời rạc, ghi rõ trạng thái khi lỗi, pre-maintenance backup, tắt lịch
  backup/autostart trong bảo trì và xử lý thủ công `.restore-*` trước khi thử lại.
- Backup timer từ chối xuất bản/prune nếu archive chứa `.restore-*`; tránh tạo backup "verified"
  không thể dùng trong lúc lần restore trước chưa hoàn tất.
- API và worker đều nhận ba task secret OpenAI/DeepSeek/Mistral trong overlay secret chung; giữ
  các overlay chat theo phạm vi hẹp như trước.

## Commands / Verification

- `uv run --offline --no-sync pytest -q tests/test_restore_local.py tests/test_worker_secrets.py tests/test_backup_retention.py`:
  **39 passed** (31 restore, 1 Compose secret, 7 backup).
- Failure injection ở preflight/catalogue/capacity/quiesce/staging/SQL/promotion/migration/smoke/
  cleanup/resume/live smoke; không fall-through để khởi động lại. Các lỗi sau start dừng lại dịch vụ.
- Test tar thật trong thư mục tạm chứng minh staging giữ tệp cũ; promotion/cleanup đúng. Test SQLite
  riêng kiểm object refs/hash qua helper smoke thực tế, gồm missing/corrupt object.
- Test project lock còn giữ trong stop khi lỗi; backup không publish/prune staging; explicit và
  auto team config vẫn giữ đúng Compose project. Compose config fixture kiểm mount secret thực tế.
- Ruff trên hai script và ba file test: passed. `bash -n scripts/team.sh`, CLI `--help`,
  `git diff --check`: passed.

## Known Issues / Limits

- Không apply restore trên database/tệp thật, không stop/restart live service, không build ảnh.
- Transaction PostgreSQL không rollback toàn bộ filesystem; lỗi promotion/migration có thể cần
  operator phục hồi trong trạng thái ứng dụng dừng, như đã ghi trong runbook.
- Restore media có tham chiếu MinIO cần kiểm chứng/khôi phục riêng, helper local fail closed.
- Root phụ trách full proof, live verify-only nếu phù hợp, Harness và HANDOFF/TASKS chung.

## Next Best Action

Root review helper, chạy verify-only trên backup riêng tư nếu cần, rồi chạy proof tổng hợp.
Reinstall backup timer để bản script ngoài repo nhận guard `.restore-*`; không khởi chạy restore
thật hoặc backup mới chỉ để đánh dấu nghiệm thu.
