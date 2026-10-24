# Session: Chọn và kiểm tra mô hình API cá nhân

## Context

- User request: chọn mô hình khi nhập API riêng và báo rõ khóa sai, chưa có credit,
  không hỗ trợ hoặc không có quyền với model đã chọn.
- Agent: Codex; ngày 2026-09-05, hoàn tất khoảng 15:21–15:24 UTC+7.
- Harness: high-risk intake #9, `US-CHAT-API-VALIDATION`, decision 0047 / DEC-060;
  ghi human correction intervention #1 liên kết trace #8 trước đó.

## Files Changed

- API: `app/api/chat.py`, `app/schemas/chat.py`, `app/core/localization.py`,
  `app/core/runtime_controls.py`, `app/services/chat_connections.py`,
  `app/services/providers/chat_errors.py`, `app/services/providers/openai_graph_chat.py`;
  `tests/test_chat_connections.py`, `tests/test_personal_chat_api.py` (dưới `apps/api/`).
- Web: `components/chat-api-settings.tsx` và `.test.tsx`, `app/chat/page.tsx` và
  `.test.tsx`, `app/globals.css`, `lib/api.ts`, `lib/chat.ts`,
  `e2e/personal-chat-api.spec.ts`, `e2e/chat-api-validation.spec.ts` (dưới `apps/web/`).
- Docs: `README.md`, `Docs/Research System Implementation Plan.md`, decision 0046
  follow-up/0047 mới, bốn tệp `docs/stories/chat-api-validation/`, HANDOFF/TASKS/DECISIONS
  và session này. Giữ nguyên các thay đổi không liên quan trong worktree.

## Decisions Made

- Tải models trực tiếp qua request SecretStr/HTTPS cố định; catalogue bounded 2 MB,
  tối đa 1000 model ID hợp lệ; không cache/save key hoặc provider body.
- Probe bằng adapter chat thật với tool vô hại, prompt tổng hợp, tối đa 16 output
  token, HTTP timeout 20 giây; không thực thi tool, không retry/fallback. Chỉ gọi sau
  nút bấm đã giải thích khả năng có phí. Không tự probe khi nhập key/tải models.
- Phân loại lỗi dùng chung cho probe và lượt chat, không echo thông điệp upstream.
  Phân biệt OpenAI credit/spend/usage/quota với tốc độ, DeepSeek 402 với 429. Model
  list không chứng minh số dư hay hỗ trợ chat. Nguồn: OpenAI Docs error-codes/model
  reference và DeepSeek official models/error-codes, liên kết trong decision 0047.
- React chỉ save khi verify đúng provider/model thành công, hủy và bỏ qua stale
  results. Lưu danh sách model đã probe cho đúng key tạm; phiên cũ cần kiểm tra đúng
  model cố định khi nhập lại. Giữ shared history và ephemeral credential contract.

## Commands / Tests Run

- `scripts/bootstrap-harness.sh`, intake, matrix active summary, intervention,
  story add/update/complete, durable decision add, backlog query (rỗng).
- `cd apps/api && .venv/bin/ruff check app tests` — pass; format scoped files.
- `cd apps/api && .venv/bin/python -m pytest -q` — 380/380 pass.
- Story proof: `tests/test_chat_connections.py tests/test_personal_chat_api.py -q`
  — 57/57 pass. Các case mạng/HTTP đều dùng key tổng hợp và mock, không key thật.
- `cd apps/web && npm run lint && npm run typecheck` — pass.
- `cd apps/web && npx vitest run` — 34 files / 171 tests pass.
- Dev Playwright trên `13001` và production `13000`: `e2e/graph-chat.spec.ts`,
  `e2e/personal-chat-api.spec.ts`, `e2e/chat-api-validation.spec.ts` — production
  15/15 pass qua ba viewport; dev error-selector chỉnh scope rồi rerun 3/3 pass.
- `docker restart businessaiagents-api-1 businessaiagents-frontend-1` — source-mounted
  production build 15 route và standalone start đạt. Không thay image/dependency.
- `docker exec businessaiagents-api-1 alembic current` — `3e5f7a9b1c24 (head)`.
- HTTP health `/api/v1/health` và frontend `/chat` 200; models/verify thiếu key 422
  cả trực tiếp và proxy. `/health` ngoài prefix trả 404, đã dùng đúng route health.
- Read-only chat counts: 10 sessions / 32 messages; không tạo fixture trong live DB.
- Container ID/uptime đối chiếu: chỉ API/frontend restart; worker/database và bốn
  Smart Exam giữ nguyên. Log mới không lỗi startup; `git diff --check` pass.
- Screenshot `/tmp/chat-api-validation-desktop-chrome.png` và mobile được xem trực
  quan: thông báo đọc được, hành động truy cập được qua cuộn, không overflow ngang.

## Verification Result

Hoàn tất triển khai và runtime smoke, không migration, không xóa dữ liệu, không
gọi AI bằng key thật. Bản mới ở `http://localhost:13000/chat`.

## Known Issues

- Chưa dùng tài khoản/khóa thật để gọi nhà cung cấp; mock chứng minh wiring và phân
  loại lỗi. Probe thành công không đảm bảo credit/quyền tương lai, không trả số dư.
- Danh mục provider có thể chứa model không hỗ trợ chat/tool; verify xử lý từ chối.
- Warnings Starlette/httpx deprecated và Playwright NO_COLOR có sẵn; tất cả tests đạt.
- Hai lần apply_patch lỗi cấu trúc/context trước khi ghi đã được sửa; không mất tệp.
- Khóa vẫn phải nhập lại khi rời/tải lại trang; đây là retention được chọn, không lỗi.

## Next Best Action

Người dùng tải lại `/chat`, vào API của tôi, nhập key, tải/chọn model và bấm kiểm tra
nếu đồng ý phí thử nhỏ đã ghi trên UI. Không ghi key hoặc dữ liệu tài chính vào logs.
