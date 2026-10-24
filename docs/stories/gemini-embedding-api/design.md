# Design

## Application Flow

`embedding_client_from_settings()` chọn `MistralEmbeddingClient` hoặc `GeminiEmbeddingClient`
theo `SEARCH_EMBEDDING_PROVIDER`. Cả hai dùng chung vòng thử lại và kiểm tra vector
(`_HttpEmbeddingClient`). `PgvectorProjection` gọi `embed()` cho đoạn tài liệu và
`embed_query()` cho câu hỏi; `_search_chunks` lọc theo `provider`/`model` của client.

## Interface Contract

- Gemini: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents`,
  header `x-goog-api-key`, mỗi đầu vào một request `{model, content.parts[0].text,
  outputDimensionality: 1024}`; phản hồi `{embeddings: [{values}]}` đúng thứ tự.
- Tiền tố: tài liệu `title: none | text: {đoạn}`; truy vấn `task: search result | query: {câu hỏi}`.
- Lô tối đa 100 đầu vào. 429/5xx/lỗi mạng được thử lại; với 429, thời gian chờ lấy
  `RetryInfo.retryDelay` của Google nếu có, giới hạn 20 giây.
- Mã lỗi giữ nguyên: `EMBEDDING_NOT_CONFIGURED`, `EMBEDDING_CONFIGURATION_INVALID` (thêm trường
  hợp provider/model không khớp), `EMBEDDING_PROVIDER_UNAVAILABLE`, `EMBEDDING_RESPONSE_INVALID`.
  Không đưa khóa hay nội dung phản hồi thô vào thông báo lỗi.

## Security

Khóa chỉ đi qua header, không vào URL hay log. Gói miễn phí của Gemini API cho phép Google
dùng nội dung để cải thiện sản phẩm; tài liệu tải lên sẽ được gửi đi khi RAG lập chỉ mục.
Điều này được ghi trong decision và README; chủ máy quyết định khi điền khóa.

## Data Model

Không đổi schema. Cột `provider`/`model` của `search_vector_projections` lưu `gemini` /
`gemini-embedding-2`. Đổi nhà cung cấp cần lập chỉ mục lại (RAG tài liệu hoặc `/search/rebuild`).

## UI / Platform Impact

Không đổi UI. Chat theo phạm vi tài liệu vẫn rơi về trích đoạn toàn văn khi chưa lập chỉ mục lại.

## Alternatives Considered

Xem `docs/decisions/0050-gemini-embedding-api.md`.
