# Kiểm chứng công cụ đánh giá đối chứng Research Agent

## Yêu cầu

Xác nhận đã dọn journal và tiếp tục phát triển. Codex, 2026-11-25 (Asia/Bangkok), Harness intake 34,
`US-OPTIMIZATION-PROGRAM`.

## Tệp đã thay đổi

- `apps/api/app/evaluation/research_agent.py`, `apps/api/app/operations.py` kiểm tra cặp biến thể
  và corpus khi kết luận KPI, dừng sớm khi provider lỗi nếu bật cờ.
- `apps/api/tests/test_research_eval.py`, `apps/api/tests/test_operations.py` bao phủ dữ liệu
  đối chứng lệch, hành vi dừng sớm và chi phí các lượt đã thử.
- `README.md`, `docs/evaluations/research-agent/README.md`,
  `docs/stories/optimization-program/validation.md`, `.claude/skills/research-eval/SKILL.md`
  cập nhật lệnh chạy, database đánh giá riêng và cách đọc chứng cứ.
- `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và phiên log này cập nhật tiến độ.

## Quyết định

- Tiếp tục hạng mục KPI Research Agent đang mở. Dùng một câu cho mỗi biến thể để kiểm tra quota
  và đường đo. Mốc KPI vẫn yêu cầu đủ tám câu, cùng corpus và các ngưỡng chất lượng hiện hành.
- Dùng Codex `gpt-6-luna` đang cấu hình, corpus công khai đã cố định và PostgreSQL thử được tạo
  để chạy rồi xóa. Cặp artifact cũ vẫn có bảng chẩn đoán để đọc lại.

## Lệnh và kết quả kiểm chứng

- `df -B1 /`, `journalctl --disk-usage`, `systemctl is-active systemd-journald` xác nhận còn
  9,74 GB trống trên `/`, 398 MiB journal và dịch vụ active. `GET /api/v1/health` ở `:18000`
  và `GET /graph` ở `:13000` trả 200.
- `scripts/bootstrap-harness.sh` và `scripts/bin/harness-cli query matrix --active --summary`
  xác nhận story đang mở. Ghi intake 34.
- Trong `apps/api`, `PYTHONPATH=. uv run --frozen python -m pytest -o addopts= -q
  tests/test_research_eval.py tests/test_operations.py tests/test_research_agent.py
  tests/test_cli_providers.py` đạt 114 ca với một cảnh báo Starlette đã có. Ruff các tệp Python
  thay đổi và `git diff --check` đạt.
- `scripts/bin/harness-cli story verify US-OPTIMIZATION-PROGRAM` đạt. Bộ API có 937 ca thu thập,
  933 đạt và 4 bỏ qua. Vitest 236 ca đạt trong 45 tệp. Có cảnh báo của Starlette và Vite.
- Preflight trả JSON tổng hợp theo schema qua Codex. Chạy `alembic upgrade head` trên PostgreSQL
  thử rồi chạy `research-eval` cho từng variant với `--questions q1-market-size`,
  corpus `research-corpus-20261119.json` và `--stop-on-provider-error`. Cả hai thoát 0. Đã xóa
  database thử, xác nhận không còn tên database của phiên thử trong `pg_database`.
- `research-eval-compare` trả chẩn đoán dưới đây và giữ trống cột thay đổi do thiếu câu và thiếu
  độ phủ góc nhìn. Chạy lại comparator trên cặp artifact lịch sử 2026-11-19 vẫn giữ kết quả
  chưa đủ điều kiện KPI. Artifact lần này nằm trong cache cục bộ
  `~/.cache/business-ai-agents/audit-runtime/20261125-paired-smoke-y90eqc84/`.

| `q1-market-size` | `reference` | `optimized` |
| --- | ---: | ---: |
| Trạng thái | Hoàn tất | Hoàn tất |
| Số lần gọi có usage | 8/8 | 8/8 |
| Tổng token | 115.287 | 114.909 |
| Thời gian (giây) | 109,8 | 105,7 |
| Độ phủ trích dẫn | 100% | 100% |
| Độ phủ góc nhìn | 80% | 80% |

## Vấn đề còn mở

Cả hai biến thể thiếu một trong năm góc nhìn kỳ vọng. Artifact lưu tỷ lệ tổng hợp. Tên từng góc
nhìn có trong metrics của lượt chạy, cần đọc trước khi xóa database ở lần đo tiếp theo. Lượt
mẫu có một câu, còn bộ đánh giá đầy đủ có tám câu. Story vẫn `in_progress`.

## Việc tiếp theo

Kiểm tra kết quả theo từng góc nhìn của `q1-market-size` để tìm phần thiếu. Tiếp tục dùng mẫu
nhỏ để xác nhận cải thiện trước khi đo toàn bộ tám câu với cả hai biến thể.
