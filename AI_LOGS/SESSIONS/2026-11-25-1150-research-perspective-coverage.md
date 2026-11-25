# Độ phủ góc nhìn trong báo cáo Research Agent

## Yêu cầu

Tiếp tục hạng mục tối ưu Research Agent, truy nguyên 4/5 góc nhìn của mẫu trước. Codex,
2026-11-25 (Asia/Bangkok), Harness intake 35, `US-OPTIMIZATION-PROGRAM`.

## Tệp đã thay đổi

- `apps/api/app/services/research_agent/runner.py` cập nhật prompt trích xuất, gọi bước bổ sung
  mục và ghi các mục được bổ sung trong báo cáo và metrics.
- `apps/api/app/services/research_agent/writer.py` dùng nguyên văn một nhận định đã kiểm chứng
  để bổ sung mỗi mục bị bỏ sót có bằng chứng.
- `apps/api/app/evaluation/research_agent.py` lưu tên góc nhìn có evidence, góc nhìn xuất hiện và
  mục được bổ sung trong artifact JSON của từng câu.
- `apps/api/tests/test_research_agent.py` và `apps/api/tests/test_research_eval.py` bổ sung hai ca
  hồi quy. Cập nhật tài liệu đánh giá, thiết kế và kiểm chứng cùng các log bàn giao.

## Phát hiện và quyết định

- Dùng Codex `gpt-6-luna`, corpus công khai cố định và database thử riêng. Kiểm tra số nguồn,
  nhận định và mục của từng góc nhìn trước khi xóa database. Giữ ngưỡng KPI hiện hành.
- Trước sửa, `reference` có 5/5 góc nhìn, `optimized` có 2/5. `optimized` đọc được 2 nguồn tìm
  từ truy vấn đối thủ nhưng không trích nhận định nào thuộc góc nhìn đó. Bản nháp bỏ cả mục kỹ
  thuật và rủi ro mặc dù đã có lần lượt 3 và 4 nhận định được kiểm chứng.
- Prompt dùng góc nhìn của truy vấn như gợi ý khi trích đoạn liên quan trực tiếp hỗ trợ. Writer
  chỉ được bổ sung mục bằng nguyên văn nhận định qua kiểm chứng, vẫn bắt buộc gắn trích dẫn và
  ghi rõ khoảng trống khi chưa có nhận định đạt chuẩn.

## Lệnh và kiểm chứng

- `scripts/bootstrap-harness.sh`, ghi intake 35, xác nhận story mở bằng
  `scripts/bin/harness-cli query matrix --active --summary`.
- Trong `apps/api`, `PYTHONPATH=. uv run --frozen python -m pytest -o addopts= -q
  tests/test_research_eval.py tests/test_research_agent.py tests/test_research_execution_guards.py
  tests/test_operations.py` đạt 112 ca. `ruff check` và `git diff --check` đạt.
- `scripts/bin/harness-cli story verify US-OPTIMIZATION-PROGRAM` đạt. API 935 ca đạt, 4 bỏ qua.
  Web 236 ca đạt trong 45 tệp.
- Phép đo dùng `alembic upgrade head` và `run_eval` với `q1-market-size` trên PostgreSQL tách
  biệt. Artifact chứa chỉ số và chẩn đoán nằm ngoài repo tại
  `~/.cache/business-ai-agents/audit-runtime/20261125-perspective-UOBkiS/`.
- Sau sửa, hai artifact đối chứng có cùng checksum corpus và fingerprint mã nguồn. Cả hai
  hoàn tất, có đủ usage. Comparator chỉ còn lý do thiếu phạm vi tám câu. Database thử đã xóa.
- Không có job đang chạy/chờ trong ba hàng đợi. `docker compose restart --timeout 60 worker`
  nạp mã mới, log xác nhận worker dừng và lên đầy đủ. API health và `/graph` trả HTTP 200.

| `q1-market-size` sau sửa | `reference` | `optimized` |
| --- | ---: | ---: |
| Độ phủ góc nhìn | 5/5 | 5/5 |
| Độ phủ trích dẫn | 100% | 100% |
| Độ phủ thực thể | 40% | 40% |
| Số lần gọi có usage | 9/9 | 8/8 |
| Tổng token | 82.411 | 82.516 |
| Thời gian (giây) | 135,1 | 112,3 |
| Mục máy chủ bổ sung | — | Đối thủ, Kỹ thuật |

## Vấn đề còn mở và bước tiếp theo

Phép đo chỉ có một câu. Để kiểm chứng KPI chi phí toàn pipeline, chạy đủ tám câu trên cả hai biến
thể với cùng corpus, cấu hình và mã nguồn, dùng database tách biệt và cờ dừng khi provider lỗi.
Story vẫn `in_progress`.
