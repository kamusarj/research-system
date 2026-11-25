# Research grounding and evaluation remediation

## User request

Thực hiện các đề xuất audit và thử Mistral. Phiên con này xử lý writer, usage và evaluation;
root quản lý intake #19 / US-AUDIT-REMEDIATION, Mistral, kiểm thử tổng và bàn giao chung.

## Files changed

- `apps/api/app/services/research_agent/writer.py`
- `apps/api/app/services/research_agent/runner.py`
- `apps/api/app/evaluation/research_agent.py`
- `apps/api/tests/test_research_agent.py`
- `apps/api/tests/test_research_eval.py`
- `docs/evaluations/research-agent/README.md`

## Decisions made

- Writer chỉ chọn/thứ tự claim; máy chủ dựng nguyên văn verified claim và citation riêng, không
  suy tính đúng nghĩa từ lexical overlap. Tiêu đề báo cáo lấy từ câu hỏi đã có của người dùng.
- Giữ usage/prompt chars của mọi attempt, kể cả phản hồi lỗi sau khi provider đã báo token;
  observation toàn cục vẫn ghi outcome error. Thiếu usage được đếm rõ.
- Giữ naive lịch sử; thêm reference cùng bật entailment, tắt tối ưu để đối chứng công bằng.
- Summary chi phí tính tổng mọi run; manifest/eligibility chặn câu hỏi thiếu, model đổi theo câu,
  thiếu usage, quality không đạt hoặc corpus/config/code không đồng nhất.
- Corpus công khai tạo tệp riêng ngoài repo, độc quyền 0600; không đọc kho nội bộ, không fallback
  mạng khi replay. Root chạy benchmark thật riêng sau khi các nguồn code ổn định.

## Commands/tests run

```text
cd apps/api
uv run --offline --no-sync ruff check app/services/research_agent/writer.py app/services/research_agent/runner.py app/evaluation/research_agent.py tests/test_research_agent.py tests/test_research_eval.py
PYTHONPATH=. uv run --offline --no-sync pytest tests/test_research_agent.py tests/test_research_eval.py
```

## Verification result

Ruff đạt; 77 test đạt trong 2,52 giây. Có regression negation/entity/appended facts, perspective
và một claim mỗi citation; failed usage/global outcome; summary chi phí lỗi; manifest/paired model/
finite quality; corpus bounds/private URL/checksum/replay không mạng; đường dẫn container `/app`.
Ban đầu targeted pytest thiếu PYTHONPATH làm import tests thất bại; lệnh có PYTHONPATH như trên đạt.
Root phát hiện giả định parents[4] không đúng container; đã thay bằng tìm marker và fallback API root.

## Known issues

- Starlette TestClient có deprecation warning từ httpx, không ảnh hưởng kết quả.
- Chưa xác nhận KPI giảm 20% bằng test fixture. Root giữ trách nhiệm paired8/model thật.
- Replay cố định nguồn không chứng minh độ trễ tìm kiếm live web.
- Không sửa shared HANDOFF/TASKS/Harness từ phiên con để tránh ghi đè root.

## Next best action

Root chạy toàn bộ API/web/bot, xuất corpus công khai từ eval cũ và đo reference/optimized bằng
provider thật trong database tách biệt; ghi rõ quality gates nào chưa đạt trước khi kết luận KPI.
