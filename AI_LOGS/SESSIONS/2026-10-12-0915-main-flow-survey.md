# Session: Khảo sát luồng hoạt động chính

## Context

- User request: kiểm tra luồng hoạt động chính hiện tại của project.
- Agent: Claude Code; ngày 2026-10-12, khoảng 09:15 UTC+7. Chỉ đọc code, cấu hình runtime
  và đếm bản ghi DB; không sửa code/container/dữ liệu.

## Files Changed

- Chỉ AI_LOGS: `HANDOFF.md`, `TASKS.md` và session này.

## Findings

- Runtime: Next.js standalone `13000` rewrite `/api/v1/*` → `http://api:8000`
  (`apps/web/next.config.ts`); FastAPI `API_WORKERS=4`, `API_RELOAD=false`;
  `worker` (`app/worker.py`) lặp `run_pending_submissions` + `run_pending_documents`,
  claim bằng `FOR UPDATE SKIP LOCKED` + lease, retry lũy tiến hữu hạn.
- Config đang chạy (không bí mật): `AUTH_MODE=disabled`, `AI_PROVIDER=mistral`,
  `GRAPH_CHAT_DEFAULT_PROVIDER=deepseek`, graph/search/vector = `postgres`,
  storage `local`, Browserless/OCR tắt. Discord bot không chạy (profile riêng).
- Luồng URL: `POST /links` hoặc `/intake-receipts` → `link_submissions` pending → worker
  `process_submission` (fetch + adapter + dedupe hash/URL + AI `LinkClassification`) →
  `needs_review` → `approve_submission` tạo `research_items` (draft→in-review→approved),
  `create_link_change_set` (draft) và `detect_gaps`. Auto-approve chỉ khi cờ bật và đủ
  confidence.
- Luồng tài liệu: `POST /documents` → `process_document` (extract → paper-fit →
  document graph riêng → `refresh_document_rag`) → `needs_review`.
- Đồ thị chuẩn chỉ đổi qua `graph_changes`: draft → validate → approve → apply
  (`apply_change_set` validate lại, chỉ áp mutation `accepted`, có compensate).
- Chat: `run_chat_turn` vòng tool có giới hạn, đề xuất ghi `GraphChangeSet(origin_type="chat")`.
- DB snapshot: link_submissions 37 (11 approved, 18 rejected, 4 duplicate, 4 failed);
  research_items 79 approved/3 draft/1 archived; document workspaces 2; change sets
  link 7 draft + 1 needs_review, chat 2 draft + 1 needs_review, document 1 applied;
  chat 10 sessions/32 messages; knowledge_gaps 63; intake_receipts 159; collector_runs 1.
- Quan sát: `outbox_events` 249 dòng, 0 `processed`; không có code nào đọc/đánh dấu
  processed. Chỉ ghi nhận, chưa xử lý.

## Commands / Tests Run

- Đọc `README.md`, `apps/api/app/{main,worker}.py`, `api/router.py`,
  `services/{ingestion,document_processing,link_mapping,graph_changes,research}.py`,
  `apps/web/next.config.ts`, `components/app-shell.tsx`, `docker-compose*.yml`.
- `docker exec businessaiagents-api-1 printenv` (chỉ biến không bí mật).
- `docker exec businessaiagents-database-1 psql ... select count(*)` (read-only).

## Next

- Chủ sở hữu quyết định xử lý các change set đang draft/needs_review.
- Nếu muốn dùng outbox, cần quyết định consumer hoặc bỏ ghi; hiện chỉ tăng dần.
