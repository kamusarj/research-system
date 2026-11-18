# Current Handoff

Cập nhật 2026-11-18. Bản trước (local readiness) giữ tại
[archive](ARCHIVE/2026-11-18-before-deployed-local-models-HANDOFF.md). Task board: [TASKS.md](TASKS.md).
Session gần nhất: [2026-11-18-1648](SESSIONS/2026-11-18-1648-deployed-local-models-completion.md).

## Current Goal

`US-DEPLOYED-LOCAL-MODELS` (intake #17, decision 0055) đã implemented và Harness `story complete` đạt:
Ollama và máy chủ OpenAI-compatible local dùng được cho chat/JSON qua endpoint operator, cùng máy hoặc
máy cá nhân qua SSH/VPN. Bước tiếp theo là operator cài model thật để nghiệm thu, rồi Linh duyệt UI.

## Current Runtime

- UI: http://localhost:13000; API: http://localhost:18000/api/v1. Cổng chỉ bind 127.0.0.1.
- `AUTH_MODE=local`, `RESEARCH_AGENT_ENABLED=true`; owner đã tạo; anonymous dữ liệu 401, mutation thiếu
  CSRF 403. Credential chỉ trong `~/.config/business-ai-agents/owner-login.json` mode 0600 ngoài repo.
- AI tác vụ/chat mặc định Codex `gpt-6-luna`, effort low; embedding vẫn Mistral. Không tự đổi provider.
- Frontend chạy bản build production trong volume `businessaiagents_frontend_next`; command của compose
  multi-user build lại từ source khi container khởi động. Nếu sửa web mà build cache cũ hơn mtime file,
  xoá volume rồi `up -d frontend` để build sạch (đã làm lần này).
- `local-ai` profile: `ollama-bridge` (172.17.0.1:11435, `/api/tags|version|generate|chat`) và
  `local-openai-bridge` (172.17.0.1:11437, `/v1/models`, `/v1/chat/completions`). Cả hai host-network,
  không mở ports, read-only, cap-drop ALL; team dùng image đóng gói, không mount source. Env cấu hình:
  `OLLAMA_BASE_URL/MODEL/API_KEY`, `LOCAL_OPENAI_BASE_URL/API_KEY/MODEL`, `LOCAL_AI_MAX_RESPONSE_BYTES`;
  upstream bridge: `OLLAMA_BRIDGE_UPSTREAM`, `LOCAL_OPENAI_BRIDGE_UPSTREAM` (loopback hoặc đầu tunnel).
- API/worker UID/GID 10001, root/source read-only, cap-drop/no-new-privileges; backup timer 02:30 giữ 14
  bản tại `~/business-ai-agents-backups/scheduled/`; tunnel gate vẫn bật. Không đụng container project khác.
- Đĩa root rất chặt (≈650MB trống sau khi dọn cache frontend). Không build TeX/team nếu chưa đủ đĩa.

## Completed This Session

- Sửa 3 test fail còn lại: tool-call local không hợp lệ fail-closed theo error contract chuẩn (502 +
  `error.code` + message thất bại lưu DB + 0 graph change set); compose config test bật profile `local-ai`.
- Nối Compose: env local model cho api/worker, `LOCAL_MODEL_BRIDGE_PROTOCOL` cho ollama-bridge, service
  `local-openai-bridge`, overlay team đóng gói cả hai bridge; `.env.example` + README runbook cập nhật.
- Cập nhật test cũ theo transport mới (`/api/chat` qua `local_models._request`) và registry có
  `local_openai`; full API suite xanh, ruff sạch.
- Sửa E2E: thêm `aria-label` tường minh cho select provider/model (label bao select gộp text option),
  spec local models đạt 6/6 trên runtime thật; 2 spec chat cũ đạt 6/6.
- Recreate api/worker/frontend với code + env mới; health 200; route local models trả 401 `AUTH_REQUIRED`.
- Điền evidence `docs/stories/deployed-local-models/validation.md`; Harness trace/checkpoint + story
  complete; cập nhật AI_LOGS. Commit triển khai `287aa76` đã push lên `feature/research-system-mvp`.

## Verification

- API: full pytest xanh (gồm local models, bridge, compose config, collector/registry); `ruff` sạch.
- Web: vitest 44 file/223 test; typecheck + eslint sạch.
- Playwright: `local-chat-models` 6/6 (desktop/tablet/mobile × ollama/local_openai) trên :13000;
  `personal-chat-api` + `chat-api-validation` 6/6.
- Harness: `story complete US-DEPLOYED-LOCAL-MODELS` pass, unit/integration/e2e/platform = 1.
- Chưa chứng minh: model thật đã cài trả lời end-to-end; endpoint SSH/VPN thật. Không tải model.

## Remaining / External Inputs

- Operator cài Ollama hoặc LM Studio model, đặt env, chạy `--profile local-ai`, kiểm tra chat/JSON thật.
- OpenAI preflight `CHAT_API_KEY_INVALID`; Gemini thiếu key; Claude billing; ChatGPT plan chưa có OAuth
  consent/client ID; team HTTPS chưa có tên miền; offsite backup chưa có đích — giữ nguyên như bản trước.
- KPI token toàn pipeline 8 câu vẫn mở (`US-OPTIMIZATION-PROGRAM`).
- Chỉ Linh quyết định product acceptance Graph v2/UI và apply các draft change set.
- Đĩa root chặt; không prune tài nguyên project khác hoặc ảnh rollback `*:pre-hardening-20261103`.

## Next Best Action

Cài một model thật trên máy chủ (hoặc tunnel từ máy cá nhân), đặt `OLLAMA_MODEL`/`LOCAL_OPENAI_MODEL` và
env bridge tương ứng, chạy `docker compose --profile local-ai up -d --build ollama-bridge
local-openai-bridge`, rồi thử `/chat`: tải danh sách, kiểm tra, tạo phiên pin model. Ghi riêng kết quả
model thật (không dùng fixture) trước khi Linh nghiệm thu UI.

## Locked Direction

Local-first; PostgreSQL source of truth; graph/search là projection; `/api/v1`; deployable code dưới
`apps/`; RSS MVP; AI không tự ghi đè human fields; báo cáo và graph proposals cần human review.
Kế hoạch: `Docs/Research System Implementation Plan.md`. Không tự migration/retire local objects
sang MinIO production, không tự ký product acceptance, không ghi secret/PII vào AI_LOGS.
