# Session: Embedding qua Gemini API miễn phí

## Context

- User request: hỏi model embedding nào tốt hơn mà vẫn miễn phí; sau đó: "embed k dùng local
  nhé, dùng api đi".
- Agent: Claude Code. Date: 2026-10-23 ~23:30 – 2026-10-24 00:40 Asia/Bangkok.
- Harness: intake #12 high-risk; story `US-GEMINI-EMBEDDING-API` (in_progress, chờ khóa);
  decision 0050 / DEC-063.

## Work Done

- Files changed:
  - `apps/api/app/services/search_projection.py`: `EmbeddingClient` protocol, `_HttpEmbeddingClient`
    (vòng thử lại + kiểm tra vector dùng chung), `MistralEmbeddingClient` (giữ hành vi),
    `GeminiEmbeddingClient`, `embedding_client_from_settings()`, `embed_query`, lọc provider/model.
  - `apps/api/app/core/config.py` (`Literal["mistral", "gemini"]`), `apps/api/app/api/search.py`,
    `apps/api/app/services/document_rag.py`, `apps/api/app/services/graph_chat.py`,
    `apps/api/scripts/verify_search_projections.py`.
  - Tests: `apps/api/tests/test_search_projections.py` (13 test mới), `apps/api/tests/test_graph_chat.py`.
  - Docs: `.env.example`, `README.md`, `docs/decisions/0050-gemini-embedding-api.md`,
    `docs/stories/gemini-embedding-api/*`, `AI_LOGS/{HANDOFF,TASKS,DECISIONS}.md`.
- Behavior changed: có thể chọn Gemini làm nhà cung cấp embedding; truy vấn dùng `embed_query`;
  tìm kiếm pgvector bỏ qua vector của provider/model khác. Runtime vẫn Mistral.

## Reasoning / Decisions

- `gemini-embedding-2`: có gói miễn phí (giá trả phí $0,20/1M token), 8.192 token đầu vào,
  Matryoshka 128–3072 nên giữ 1024 chiều, không migration. Đã so với Voyage/Jina/Cohere/Cloudflare
  Workers AI (miễn phí một lần hoặc model yếu hơn) và `gemini-embedding-001` (2.048 token).
- Không có `task_type` trên model 2, nên dùng tiền tố Google khuyến nghị cho truy hồi bất đối xứng.
- Lọc theo provider/model để vector Mistral cũ không bị xếp hạng với truy vấn Gemini; chat theo
  tài liệu tự rơi về trích đoạn toàn văn khi không có đoạn khớp.
- Không tự đặt provider=gemini trong `.env` khi chưa có khóa (sẽ làm hỏng RAG tài liệu).

## Verification

- Commands run: `.venv/bin/pytest tests/test_search_projections.py tests/test_graph_chat.py`;
  `.venv/bin/python -m pytest` (toàn bộ API; `pytest` trực tiếp lỗi import `tests` ở
  `test_intake_review_backlog.py`, có từ trước); `ruff check app scripts tests`; `ruff format --check`
  các tệp đã sửa; `docker restart businessaiagents-api-1 businessaiagents-worker-1`; gọi
  `embedding_client_from_settings()` trong container.
- Result: 460/460 passed; Ruff sạch; health 200; Mistral thật `embed_query` + `embed` 1024 chiều,
  1,31 giây.

## Known Issues

- Chưa gọi thật Gemini (chưa có `GEMINI_API_KEY`).
- Gói miễn phí Gemini: Google được dùng nội dung để cải thiện sản phẩm; giới hạn tốc độ chỉ thấy
  trong AI Studio.
- `systemctl --user restart business-ai-agents.service` không tạo lại container; phải
  `docker restart` API/worker để nạp code.
- 35 tệp lệch `ruff format` từ trước (gồm `scripts/verify_search_projections.py`), không sửa.

## Next Best Action

- Chủ máy điền `GEMINI_API_KEY`; agent chuyển `.env`, restart, gọi thật, lập chỉ mục lại RAG
  3 tài liệu, rồi `harness-cli story complete`.
