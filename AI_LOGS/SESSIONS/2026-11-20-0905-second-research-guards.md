# Second audit — research execution guards

## User request

User cho phép sửa12 phát hiện audit. Phiên con này xử lý5 lỗi research; root quản lý intake21,
high-risk `US-SECOND-AUDIT-REMEDIATION`, decision0057 và bàn giao chung.

## Files changed

- `apps/api/app/models.py`: nullable `ResearchRun.lease_token` và unique index.
- `apps/api/migrations/versions/8e0a2c4d6f79_add_research_run_lease_fencing.py`.
- `apps/api/app/services/research_agent/runner.py`: claim CAS/fencing, verifier/cache guards.
- `apps/api/app/services/research_agent/writer.py`: phân biệt omission và thiếu evidence.
- `apps/api/app/services/research_agent/evidence.py`: computation budget tất định.
- `apps/api/tests/test_research_agent.py`: helper retry fixture dùng claim thật/đồng hồ giả.
- `apps/api/tests/test_research_execution_guards.py`:17 regression, hỗ trợ PG tách biệt.
- `apps/api/tests/test_migrations.py`: giữ nguyên dữ liệu run trước migration.
- `docs/evaluations/research-agent/README.md`: hợp đồng thực thi/triển khai cập nhật.

## Decisions made

- Mỗi claim nhận UUID mới; context giữ token bất biến. CAS kiểm id/token/status/deadline/cancel
  trước heartbeat, commit kết quả/lỗi và sau I/O. Dùng no-autoflush trước CAS; stale worker rollback
  cả cache/report/counters đang chờ. Không giữ khóa hàng qua model/search/fetch. Cancel thu hồi token.
- Fencing chỉ bảo vệ worker đã nâng phiên bản: phải dừng API/worker cũ trước migrate/restart;
  không rolling mix với binary cũ. Migration chỉ additive, existing run không đổi nội dung.
- Duplicate/unknown judgement ID vô hiệu cả lô; cùng claim/evidence có verdict mâu thuẫn qua alias
  khác nhau thì bỏ tất cả verdict đó. Không ghi chúng vào cache.
- Chỉ cache verdict từng claim đã kiểm tra, TTL24h; bỏ qua whole-batch cache cũ. Prompt entailment
  v3 vô hiệu cache cũ có thể được tạo trước guard ID/conflict; không đổi baseline/quality gates.
- Report vẫn đo coverage thật: ghi rõ đã có verified claim nhưng chưa tổng hợp, không tự thêm
  section để tăng điểm. Không đánh đồng writer bỏ sót với không có evidence.
- Fuzzy matching giới hạn250000 phép so sánh token ước lượng, khử trùng cửa sổ; hết budget trả
  không khớp. Exact/normalized giữ nguyên.

## Commands/tests run

```text
cd apps/api
uv run --offline --no-sync ruff check app/services/research_agent/runner.py app/services/research_agent/writer.py app/services/research_agent/evidence.py app/models.py tests/test_research_execution_guards.py tests/test_migrations.py
PYTHONPATH=. uv run --offline --no-sync pytest tests/test_research_agent.py tests/test_research_eval.py tests/test_research_execution_guards.py tests/test_migrations.py
git diff --check
```

## Verification result

104 targeted test đạt trong9,71 giây; Ruff và diff check đạt. Bao gồm migration upgrade/check/
downgrade/reapply và giữ nguyên synthetic running run trước migration.
17 guard case bao gồm8 lease case với2 Session xen kẽ: worker mới completed trước khi worker cũ
trả về; late success/provider error/retryable/permanent/unexpected; pending report/cache rollback;
stale heartbeat và cancellation. Verifier conflict/TTL, gap messages và computation budget đều đạt.

Test hỗ trợ PostgreSQL qua `RESEARCH_LEASE_TEST_DATABASE_URL`, chỉ chấp nhận database đã migrate
có tên `baa_ci_*`. Root chạy proof PostgreSQL riêng; phiên con không chạm database thật.
Không gọi model thật, không chạy lại benchmark, không sửa artifact eval lịch sử.

Root chạy PostgreSQL lần đầu:15/17 đạt;2 case bị cache planning của case trước làm provider
callback không chạy (SQLite từng test có database mới nên không thấy vấn đề fixture này).
Đã thêm cache salt riêng cho mỗi lease case, giữ salt của cùng run khi worker thay thế và salt
cố định riêng cho test verifier TTL; thêm assert callback phải thực sự chạy. Không nới assertion
fencing, không sửa production code. Chạy lại17 case SQLite đạt0,92 giây; root đo lại PG riêng.

## Known issues

- Starlette TestClient có deprecation warning httpx; không ảnh hưởng proof.
- Benchmark20%, hạn mức Codex, tier/rate limit Mistral và local-model thật vẫn là proof khác.
- Old worker chưa nâng cấp không thể được bảo vệ chỉ bằng thêm column; cần quiesce triển khai.
- Không ghi shared HANDOFF/TASKS/Harness từ phiên con để tránh ghi đè root.

## Next best action

Root chạy guard tests trên PostgreSQL tách biệt, review/full suite, rồi quiesce API/worker và migrate
runtime. Ghi evidence cuối vào validation/session tổng, không tự kết luận KPI từ regression fixture.
