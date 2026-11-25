# Design

Kế hoạch đầy đủ đã được chủ sở hữu duyệt ngày 2026-10-24 (giai đoạn 0–4). Tóm tắt các điểm thiết
kế bền vững; chi tiết pipeline bổ sung khi triển khai giai đoạn 3A.

## Domain Model

- `ResearchRun`: một câu hỏi nghiên cứu, trạng thái + giai đoạn, ngân sách, số đo; kết quả là một
  `ResearchItem` draft loại `deep-research-report`.
- Nguồn, claim và sự kiện tiến độ của run lưu riêng để kiểm chứng và phát lại SSE.

## Application Flow

planner (câu hỏi → góc nhìn × truy vấn) → searcher (SearXNG/kho nội bộ, fetch an toàn qua
`fetch_public`, cache, dedup) → verifier (khớp trích dẫn nguyên văn + kiểm tra suy luận) →
writer (chỉ dùng claim đã xác minh, validator bắt buộc `[n]`).

Tìm kiếm duyệt hit đạt ngưỡng liên quan theo hạng trước (`rank-first round-robin`) để mỗi góc
nhìn nhận các nguồn phù hợp nhất trước khi truy vấn khác chiếm URL trùng. Trích xuất ưu tiên góc
nhìn của truy vấn khi nguồn có trích đoạn liên quan hỗ trợ trực tiếp và giữ nguyên tên tổ chức/sản
phẩm/chuẩn từ trích dẫn gốc.
Ở biến thể `optimized`, cờ `passage_filter` chọn các đoạn nguyên văn giàu thông tin (khớp truy
vấn/góc nhìn, số liệu, thực thể, bỏ boilerplate; giới hạn 5.200 ký tự/nguồn và tối đa 4 nguồn/lô)
từ `source.content_text` mà không sửa ký tự gốc, trong khi đối chiếu trích dẫn và kiểm tra suy luận
vẫn chạy trên toàn văn nguồn gốc; `reference` và `naive` giữ `passage_filter=False`.
Nếu bản nháp hợp lệ bỏ sót một góc nhìn đã có nhận định được kiểm chứng, máy chủ dựng một mục với
nguyên văn nhận định và link nguồn. Góc nhìn chưa có nhận định đạt chuẩn vẫn hiển thị là khoảng
trống bằng chứng.

## Interface Contract

- Mới, additive: `/api/v1/research-runs` (tạo, danh sách, chi tiết, `/events` SSE, hủy, xuất
  Markdown). Không đổi route hiện có.

## Data Model

- Bảng mới additive (migration Alembic), cột usage additive trên `ai_outputs`.

## UI / Platform Impact

- Trang `/research/new` + màn chạy; trình đọc báo cáo; design token + dark mode.
- Compose: thêm service `searxng` (mạng nội bộ, không publish cổng); cổng cục bộ bind 127.0.0.1.

## Observability

- Usage token/độ trễ mỗi lời gọi AI trong `ai_outputs` + Prometheus; sự kiện run.

## Alternatives Considered

1. API search trả phí (Brave/Tavily) — để sau qua `SearchProvider`.
2. Chỉ kho nội bộ — độ phủ thấp.
