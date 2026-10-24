# Session: Đánh giá chuyển sang OpenRouter miễn phí

## Context

- User request: chuyển sang dùng OpenRouter với chi phí miễn phí có được không.
- Agent: Claude Code; ngày 2026-10-12, khoảng 09:45 UTC+7. Chỉ đánh giá, không sửa code,
  không gọi API trả phí, không dùng khóa.

## Files Changed

- Chỉ AI_LOGS: `HANDOFF.md`, `TASKS.md` và session này.

## Findings

- Code: `OpenRouterProvider` (`apps/api/app/services/ai.py`) dùng Chat Completions,
  `strict_schema=True` (cần model hỗ trợ structured outputs). Dùng bởi
  `provider()` trong ingestion, document_processing, document_editing,
  document_instant_edit, document_graph_research khi `AI_PROVIDER=openrouter`.
- Chưa hỗ trợ: graph chat (`graph_chat_provider` chỉ openai/deepseek,
  `app/services/providers/openai_graph_chat.py`), API cá nhân (`schemas/chat.py`
  Literal openai/deepseek), embedding (`search_embedding_provider: Literal["mistral"]`,
  cột vector 1024 chiều).
- OpenRouter docs `api-reference/limits`: model `:free` 20 req/phút; 50 req/ngày nếu
  mua < 10 credit, 1000 req/ngày nếu ≥ 10 (tính tổng đã mua). Số dư âm có thể bị 402 kể
  cả model free.
- `GET https://openrouter.ai/api/v1/models` (công khai) ngày 2026-10-12: 458 model, 19
  giá 0. Có tools + structured_outputs: `nvidia/nemotron-3-super-120b-a12b:free`,
  `openrouter/free`, `apodex/apodex-1.1-mini:free`, `dots-studio/dots-3-note-preview:free`,
  `liquid/lfm-2.5-2.6b:free`. Embedding free: `liquid/lfm-2.5-embedding-350m:free`,
  `nvidia/nemotron-3-embed-1b:free`, `nvidia/llama-nemotron-embed-vl-1b-v2:free`.
- Ước lượng tải: 1 link ≈ 1 request; 1 tài liệu ≈ 2–3; 1 lượt chat tối đa ~5
  (`CHAT_MAX_TOOL_LOOPS=4`).
- Privacy docs: cài đặt riêng cho endpoint free/paid có thể train trên prompt; cần kiểm
  tra chính sách từng endpoint vì app gửi tối đa 30.000 ký tự nội dung nguồn.

## Commands / Tests Run

- Đọc `app/services/ai.py`, `app/core/config.py`, `app/services/providers/openai_graph_chat.py`,
  `app/schemas/chat.py`, `app/models.py`.
- `curl https://openrouter.ai/api/v1/models` và `/api/v1/embeddings/models` (công khai,
  không khóa) vào scratchpad; WebFetch/WebSearch tài liệu OpenRouter.

## Next

- Chủ sở hữu chọn phạm vi; nếu chỉ đổi phân loại/tài liệu: đặt `AI_PROVIDER=openrouter`,
  `OPENROUTER_MODEL=<model :free có structured outputs>`, cấp `OPENROUTER_API_KEY` qua
  secret file, recreate api + worker, rồi kiểm tra bằng một link thử.
