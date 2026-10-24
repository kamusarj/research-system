# Validation

## Proof Strategy

Chứng minh Gemini client gửi đúng request/tiền tố và kiểm tra phản hồi, factory chọn đúng client,
tìm kiếm không trộn vector khác model, và đường Mistral không đổi hành vi.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Gemini: URL/header/body, tiền tố tài liệu/truy vấn, chia lô ≤100, sai số chiều/không hữu hạn/thiếu phần tử, 429 dùng retryDelay (giới hạn), 400 không thử lại; factory: chưa có khóa, model không khớp, chọn đúng client |
| Integration | pgvector `_search_chunks` bỏ qua hàng của model khác (SQLite JSON fallback nếu áp dụng) |
| Regression | Test Mistral hiện có; toàn bộ API pytest; Ruff |
| Live | Khi có khóa: embed thật 1 truy vấn + 1 tài liệu, kiểm tra 1024 chiều; lập chỉ mục lại RAG tài liệu; chat theo tài liệu lấy được đoạn |

## Fixtures

HTTP giả qua tham số `post`; không gọi mạng trong test.

## Acceptance Evidence

- Unit/integration: `test_search_projections.py` + `test_graph_chat.py` đạt (13 test mới cho
  Gemini, factory, lọc provider/model); toàn bộ API `python -m pytest` 460/460; Ruff check sạch,
  các tệp đã sửa đúng `ruff format`.
- Runtime: API/worker khởi động lại với code mới, health 200; gọi thật qua
  `embedding_client_from_settings()` trong container (vẫn Mistral): `embed_query` + `embed`
  trả 1024 chiều trong 1,3 giây.
- Chưa có: gọi thật Gemini (chưa có `GEMINI_API_KEY`), chuyển `.env`, lập chỉ mục lại RAG tài liệu.
