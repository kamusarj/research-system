# Embedding qua Gemini API miễn phí

## Current Behavior

Embedding cho RAG tài liệu và tìm kiếm pgvector chỉ có một nhà cung cấp: Mistral
`mistral-embed` (1024 chiều, đời 2023). Truy vấn và tài liệu được embed giống hệt nhau.

## Target Behavior

Chủ máy chọn `SEARCH_EMBEDDING_PROVIDER=gemini` với `SEARCH_EMBEDDING_MODEL=gemini-embedding-2`
(gói miễn phí của Gemini API, `GEMINI_API_KEY`). Vector vẫn 1024 chiều (Matryoshka), nên không
cần migration. Truy vấn và tài liệu dùng tiền tố Google khuyến nghị cho truy hồi bất đối xứng.
Tìm kiếm chỉ so sánh vector cùng provider/model với client hiện tại, nên vector Mistral cũ
không lẫn vào kết quả trước khi được embed lại. Mistral vẫn là mặc định trong code và vẫn
chọn được.

## Affected Users

Owner/researcher ở chế độ cục bộ và nhóm (embedding là cấu hình máy chủ).

## Affected Product Docs

- `README.md`, `.env.example`
- `docs/decisions/0050-gemini-embedding-api.md`
- `AI_LOGS/DECISIONS.md` (DEC-063)

## Non-Goals

Embedding local (Ollama), đổi số chiều/migration pgvector, bật `VECTOR_DATA_PROVIDER=pgvector`
cho tìm kiếm đã duyệt, embedding đa phương thức (ảnh/PDF), Batch API giá rẻ.
