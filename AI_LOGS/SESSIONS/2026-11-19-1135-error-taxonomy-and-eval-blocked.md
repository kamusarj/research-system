# Session Log

## User request

"làm tiếp đi" — tiếp tục Next Best Action của bàn giao trước: sửa nguyên nhân `AI_RESPONSE_INVALID`
của optimized (q6-q7/q8 paired eval 2026-11-19), viết regression, đo lại paired eval. Agent:
OpenCode; 2026-11-19, Asia/Bangkok. Intake #20, normal lane, story `US-OPTIMIZATION-PROGRAM`.

## Files changed

- `apps/api/app/services/providers/cli_bridge.py`: thêm `BridgeProtocolError(ValueError)`; 
  `bridge_complete` raise mã này cho body không phải JSON / payload sai hình dạng (trước là
  `ValueError` bị map nhầm thành lỗi output model).
- `apps/api/app/services/research_agent/runner.py`: `_llm_failure_code` phân loại trung thực
  (401/403 → `AI_PROVIDER_AUTH_FAILED`, 429 → `AI_PROVIDER_RATE_LIMITED`, HTTP/transport →
  `AI_PROVIDER_UNAVAILABLE`, giao kèo cầu nối → `AI_PROVIDER_ERROR`, chỉ parse/validation →
  `AI_RESPONSE_INVALID`, khác → rỗng để caller quyết định). `_llm_one` dùng helper + bảng message;
  `stage_extracting` không gộp lỗi batch provider thành `AI_RESPONSE_INVALID` nữa, ghi sự kiện
  chẩn đoán `error_types` (commit trước khi raise để không mất theo rollback).
- `apps/api/app/services/ai.py`: `_enrichment_error` map `BridgeProtocolError` → `AI_PROVIDER_ERROR`.
- `apps/api/tests/test_research_agent.py`: 5 test regression (transport, 429 rate limit, bridge
  protocol, parse-giữ-nguyên, write-stage bridge) + assert `AI_RESPONSE_INVALID` ở test budget cũ;
  helper `_drive_until_terminal`.
- `apps/api/tests/test_cli_providers.py`: 4 case parametrize payload sai của `bridge_complete`.
- `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, session log này. Không commit/push.

## Decisions made

- Chỉ lỗi output thật của model mới mang `AI_RESPONSE_INVALID`; lỗi nhà cung cấp/cầu nối mang
  `AI_PROVIDER_*` để retry/eval không đổ lỗi chất lượng cho model. Không đổi prompt/variant/quality
  gates của eval.
- So sánh KPI đòi hỏi cùng fingerprint mã nguồn → phải đo lại CẢ reference lẫn optimized sau khi
  sửa; Linh đã duyệt chi phí (~1,3M token).
- Khi bridge trả 429 mọi lời gọi (hạn mức Codex hết): dừng đo chủ động thay vì chạy hết 16 lượt
  hỏng; giữ log bằng chứng; chờ hạn mức reset rồi chạy lại trọn bộ.

## Commands/tests run

- `uv run --frozen python -m pytest`: targeted 102 → 103 (thêm test 429) passed; full suite
  **818 passed**. `uv run --frozen ruff check . ../../scripts/backup_local.py` sạch.
- `docker compose restart api worker`; health 200.
- Probe qua bridge trong container: `configured True, available True`, `bridge_complete` →
  `HTTPStatusError 429`. Bridge log user journal 11:13–11:17: `status=429 code=CLI_RATE_LIMITED`
  mọi lời gọi.
- Paired eval rerun thử (`run-paired-eval-rerun.py`, DB `baa_ci_eval_*`, corpus 158 nguồn):
  q1/q2 reference failed `AI_PROVIDER_UNAVAILABLE` (6 calls, usage_missing 6 — cùng mẫu q6-q8 cũ),
  dừng chủ động lúc q3; drop DB, xóa artifact tạm. Progress:
  `~/.cache/business-ai-agents/audit-runtime/paired-eval-progress-rerun-20261119.log`.
- `harness-cli intake` #20; `harness-cli story update --id US-OPTIMIZATION-PROGRAM` evidence.

## Verification result

Fix + regression đạt (818 passed, ruff sạch); phân loại lỗi mới được xác nhận đúng trên lỗi thật
(429 giờ hiện `AI_PROVIDER_RATE_LIMITED` thay vì `AI_RESPONSE_INVALID`). Paired eval chưa đo lại
được do hạn mức Codex CLI — đã dừng sạch, không tốn quota, không để DB rác.

## Known issues

- **Codex CLI 429 `CLI_RATE_LIMITED`** — hạn mức subscription đã hết (đây cũng là nguyên nhân gốc
  q6-q8 lần đo trước bị ghi nhầm `AI_RESPONSE_INVALID`). Cần hạn mức reset trước khi đo lại.
- KPI20% vẫn mở; evidence cũ (quality gates KHÔNG ĐẠT) còn nguyên ở
  `docs/evaluations/audit-remediation/`.
- Mistral generation vẫn chặn bởi tier/rate limit; CI chưa commit/push; root đĩa chặt.

## Next best action

Khi hạn mức Codex reset (Linh kiểm tra gói/thời điểm reset, hoặc báo để tôi probe lại):
`python3 ~/.cache/business-ai-agents/audit-runtime/run-paired-eval-rerun.py` chạy trọn bộ 2 variant,
rồi export artifact `-r2` vào `docs/evaluations/audit-remediation/`, chạy `research-eval-compare`,
ghi kết luận quality gates và cập nhật bàn giao.
