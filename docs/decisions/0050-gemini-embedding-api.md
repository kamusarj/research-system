# 0050 Embedding qua Gemini API miễn phí (gemini-embedding-2)

Date: 2026-10-24

## Status

Accepted. Người dùng muốn một model embedding tốt hơn `mistral-embed` mà vẫn miễn phí, chạy qua
API chứ không chạy local.

## Context

Embedding (RAG tài liệu, pgvector) chỉ có Mistral `mistral-embed` (2023). Cầu nối CLI (0049)
không cung cấp embedding. Nội dung chủ yếu tiếng Anh, còn người dùng hỏi bằng tiếng Việt, nên
cần truy hồi chéo ngôn ngữ tốt. Cột `vector(1024)` có sẵn; bảng có cột `provider`/`model`.

## Decision

- Thêm nhà cung cấp `gemini` (`SEARCH_EMBEDDING_PROVIDER`), model `gemini-embedding-2` qua
  `batchEmbedContents`, khóa `GEMINI_API_KEY` đặt trong header `x-goog-api-key`, với
  `outputDimensionality=1024` (Matryoshka, API tự chuẩn hóa). Không migration.
- Truy hồi bất đối xứng bằng tiền tố của Google: tài liệu `title: none | text: …`, truy vấn
  `task: search result | query: …`. Client có `embed()` (tài liệu) và `embed_query()`.
- Tìm kiếm pgvector chỉ xếp hạng hàng có `provider`/`model` trùng client hiện tại; vector của
  model cũ bị bỏ qua cho đến khi lập chỉ mục lại.
- 429 của gói miễn phí: chờ theo `RetryInfo.retryDelay`, tối đa 20 giây mỗi lần, theo số lần
  thử lại sẵn có. Provider và tên model không khớp thì báo `EMBEDDING_CONFIGURATION_INVALID`.
- Mistral vẫn là mặc định trong code/Compose; runtime cục bộ chuyển sang Gemini khi có khóa.

## Alternatives Considered

- Qwen3-Embedding/bge-m3 qua Ollama: chất lượng tốt, riêng tư, nhưng người dùng không muốn local.
- Voyage (200M token miễn phí một lần), Jina (10M token), Cohere trial (giới hạn, không thương
  mại), Cloudflare Workers AI (10k neuron/ngày, model nhỏ): hoặc không miễn phí lâu dài, hoặc yếu hơn.
- `gemini-embedding-001`: chỉ 2.048 token đầu vào, phải tự chuẩn hóa khi cắt chiều.

## Consequences

Chất lượng truy hồi đa ngôn ngữ tốt hơn và không tốn tiền. Đổi lại, gói miễn phí cho Google dùng
nội dung để cải thiện sản phẩm, kể cả nội dung tài liệu tải lên khi RAG lập chỉ mục; giới hạn
tốc độ chỉ xem được trong AI Studio. Cần lập chỉ mục lại sau khi đổi; trong lúc chờ, chat theo
tài liệu dùng trích đoạn toàn văn.

## Follow-Up

Nếu cần riêng tư hoặc giới hạn cao hơn, bật thanh toán Gemini (dữ liệu gói trả phí không dùng để
huấn luyện) hoặc quay lại Mistral. Hiệu chỉnh `SEARCH_SEMANTIC_MAX_DISTANCE` nếu bật
`VECTOR_DATA_PROVIDER=pgvector`.
