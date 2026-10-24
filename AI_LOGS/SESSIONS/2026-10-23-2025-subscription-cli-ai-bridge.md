# Session: Dùng quota Claude Code/Codex/Antigravity thay cho API AI

## Context

- User request: “tôi cần thay đổi cách hoạt động của các AI provider. Thay vì sử dụng API, tôi
  muốn sử dụng quota của codex hoặc antigravity, hoặc claude code ... hãy lên kế hoạch và giúp tôi
  thực hiện đi”. Người dùng chọn: mặc định Codex, hỗ trợ cả ba CLI, model nhẹ.
- Agent: Claude Code. Date: 2026-10-23, ~14:30–20:25 Asia/Bangkok.
- Harness: intake #11 high-risk; story `US-SUBSCRIPTION-CLI-AI-BRIDGE` (completed với proof mới);
  decision 0049 / DEC-062.

## Work Done

- Files changed:
  - Mới: `apps/api/app/ai_cli_bridge.py`, `apps/api/app/services/providers/cli_bridge.py`,
    `apps/api/tests/test_ai_cli_bridge.py`, `apps/api/tests/test_cli_providers.py`,
    `ops/systemd/user/business-ai-agents-ai-cli-bridge.service`, `scripts/install_ai_cli_bridge.sh`,
    `docs/decisions/0049-subscription-cli-ai-bridge.md`, `docs/stories/subscription-cli-ai-bridge/*`.
  - Sửa: `apps/api/app/core/config.py`, `apps/api/app/services/ai.py`,
    `apps/api/app/services/providers/openai_graph_chat.py`, `apps/api/app/schemas/{ingestion,chat,documents}.py`,
    `apps/api/tests/test_ingestion.py`, `apps/web/app/chat/page.tsx`, `apps/web/lib/api.ts`,
    `docker-compose.yml`, `docker-compose.team.yml`, `.env.example`, `README.md`,
    `AI_LOGS/{HANDOFF,TASKS,DECISIONS}.md`.
  - Ngoài repo: `.env` (AI_PROVIDER/GRAPH_CHAT_DEFAULT_PROVIDER=codex, AI_CLI_BRIDGE_URL/TOKEN; bản
    sao lưu trong `~/business-ai-agents-backups/`), token cầu nối và unit systemd user.
- Behavior changed: API/worker gọi cầu nối trên máy chủ để chạy CLI bằng gói đăng nhập; ba nhà cung
  cấp mới trong `/ai/providers`, trang chat và preflight; chế độ nhóm tắt cầu nối.

## Reasoning / Decisions

- Cầu nối trên host thay vì cài CLI vào ảnh: phiên đăng nhập ở home chủ máy, đĩa còn ít, tránh
  lộ toàn bộ `~/.claude`/`~/.codex` và xung đột làm mới token.
- Claude Code tắt toàn bộ công cụ nên an toàn ngoài sandbox. Codex/agy không tắt hết công cụ được
  (agy của chủ máy còn cho phép `cat`, `source .env`) nên chạy trong bubblewrap; Codex gắn đúng tệp
  `auth.json`, agy lấy đăng nhập từ keyring qua xdg-dbus-proxy chỉ cho `org.freedesktop.secrets`.
- Codex strict output schema khi chuyển được; schema có object tự do (`LinkClassification.relations`)
  mô tả trong prompt; schema bị từ chối thì thử lại một lần không schema.
- Prompt lớn qua stdin (agy dùng stream-json `{"event":"user","message":{"content":...}}`) để tránh
  giới hạn 128 KiB của tham số dòng lệnh.
- Chat: tool call bằng JSON có cấu trúc `{reply, tool_calls[{name, arguments_json}]}`.
- Không thay embedding (CLI không có); không dùng gói cá nhân cho chế độ nhóm.

## Verification

- Commands run: probe headless từng CLI; `python3 -I apps/api/app/ai_cli_bridge.py probe <backend>`;
  kiểm tra cô lập sandbox (canary); `ruff check app`, `ruff format`; `pytest` 2 tệp mới (46/46);
  toàn bộ API pytest 420/420; `npx tsc --noEmit`, `npm run lint`, `npx vitest run app/chat lib`
  (55/55); `scripts/install_ai_cli_bridge.sh`; `systemctl --user restart business-ai-agents.service`;
  `docker restart businessaiagents-frontend-1`; gọi thật Codex từ container API; `harness-cli story
  complete` (pass).
- Result:
  - Claude `sonnet` 3,4 giây; Codex `gpt-6-luna` 8,1 giây; agy flash-medium 16–30 giây (lần đầu 62).
  - Sandbox không thấy canary/repo/Docker socket; env sạch; `~/.codex/auth.json` không đổi inode.
  - Container → bridge: health 200 với token, 401 token sai; không nghe loopback/LAN.
  - Codex từ container: phân loại link 8,4 giây (bỏ qua chỉ thị chèn trong nội dung), trích đồ thị
    strict 8,2 giây, chat lượt 1 gọi `search_graph`, lượt 2 trả lời tiếng Việt.
  - `/ai/providers`: codex active + chat_active, ba CLI configured/reachable; frontend healthy;
    tunnel `/chat` 200.

## Known Issues

- Tác vụ nền tiêu quota 5 giờ của gói Codex; khi hết quota lỗi `AI_PROVIDER_RATE_LIMITED`/
  `CHAT_CLI_LIMIT_REACHED` và worker thử lại theo lịch sẵn có.
- Rủi ro còn lại: prompt injection có thể khiến Codex/agy đưa token đăng nhập của chính nó vào kết
  quả (chỉ thứ đó trong sandbox). Claude Code không có rủi ro này.
- agy chậm (16–30 giây) và cần keyring đã mở khóa (đăng nhập phiên đồ họa).
- Chưa gửi link thật hay tạo chat thật qua UI (tránh ghi dữ liệu thử vào database của chủ máy).
- `apps/api/app/schemas/chat.py` lệch `ruff format` từ trước (không do phiên này).

## Next Best Action

- Chủ máy thử một link thật trên `/ingestion` và một cuộc chat trên `/chat` từ điện thoại.
- Theo dõi `journalctl --user -u business-ai-agents-ai-cli-bridge` (chỉ ghi backend/model/thời gian).
