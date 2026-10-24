# 0049 Dùng quota CLI đăng ký qua cầu nối trên máy chủ

Date: 2026-10-23

## Status

Accepted — người dùng yêu cầu thay API bằng quota Codex/Antigravity/Claude Code; chọn mặc định
Codex, hỗ trợ cả ba CLI, model nhẹ cho tác vụ nền.

## Context

Các tác vụ AI (phân loại link, xử lý tài liệu, paper-fit, sửa tài liệu, chat đồ thị) gọi API
trả phí. Chủ máy đã đăng nhập Claude Code, Codex và Antigravity (`agy`) bằng gói đăng ký, nhưng
API/worker chạy trong Docker, không có CLI hay phiên đăng nhập. Nội dung gửi cho AI có thể đến
từ trang web/tài liệu không tin cậy, còn Codex và Antigravity là agent luôn có công cụ (shell,
đọc tệp, trình duyệt); cấu hình `agy` của chủ máy còn cho phép `cat`, `source .env` trong home.

## Decision

- Thêm `apps/api/app/ai_cli_bridge.py` (chỉ thư viện chuẩn) chạy trên máy chủ dưới user service
  `business-ai-agents-ai-cli-bridge.service`, chỉ nghe `172.17.0.1:11436`, bắt buộc Bearer token
  (tệp `~/.config/business-ai-agents/ai-cli-bridge.token`, truyền vào container qua `.env`).
  `POST /v1/complete` nhận backend, model, effort, system, prompt (stdin), JSON schema;
  `GET /v1/health` chỉ báo CLI đã cài/đăng nhập, không tốn quota. Tối đa 2 lượt song song.
- Claude Code chạy `-p --tools "" --safe-mode --strict-mcp-config --setting-sources ""`
  (không có công cụ nào), `--json-schema`, model `sonnet`, effort `low`.
- Codex và Antigravity chạy trong bubblewrap: `/usr`, `/etc` chỉ đọc, `/run` và `/tmp` rỗng,
  HOME riêng trong `~/.local/state/business-ai-agents/ai-cli-bridge`, thư mục làm việc tạm,
  môi trường dựng lại từ đầu (không API key). Codex chỉ thấy đúng `~/.codex/auth.json` (gắn
  đọc-ghi để làm mới token), `--ignore-user-config`, sandbox read-only, tắt web search/trình
  duyệt/computer use/apps/plugins, `--output-schema` strict khi schema chuyển được (thuộc tính
  tùy chọn thành nullable rồi bỏ null), nếu không thì mô tả schema trong prompt; model
  `gpt-6-luna`, effort `low`. Antigravity nhận prompt qua stream-json stdin, `--json-schema`,
  model `gemini-3.8-flash-medium`, keyring chỉ qua `xdg-dbus-proxy --talk=org.freedesktop.secrets`.
- API thêm nhà cung cấp `claude_code`, `codex`, `antigravity` cho `complete_json` và chat đồ thị.
  Chat mô phỏng gọi công cụ bằng JSON có cấu trúc `{reply, tool_calls[{name, arguments_json}]}`
  với tên công cụ trong enum; công cụ lạ hoặc tham số sai bị từ chối. CLI không nhận API key cá
  nhân. Lỗi giữ ngữ nghĩa HTTP (403 đăng nhập, 429 hết quota, 504 timeout) để xử lý lỗi sẵn có
  của tác vụ nền vẫn đúng; chat có thêm `CHAT_CLI_LIMIT_REACHED`, `CHAT_CLI_LOGIN_REQUIRED`.
- Embedding (RAG tài liệu) vẫn dùng Mistral vì CLI không cung cấp embedding.
- Chế độ nhóm (`docker-compose.team.yml`) luôn đặt URL/token cầu nối rỗng: gói đăng ký là của
  một người, dùng chung cho thành viên nhóm là chia sẻ tài khoản.

## Alternatives Considered

- Cài CLI vào ảnh API/worker và gắn thư mục đăng nhập: ảnh lớn hơn (đĩa còn ít), lộ toàn bộ
  `~/.claude`/`~/.codex` (lịch sử phiên khác) cho container, xung đột làm mới token.
- Chạy Codex/agy trực tiếp trên host không sandbox: prompt injection từ trang web có thể đọc
  SSH key/`.env` qua công cụ shell của agent.
- Sao chép tệp đăng nhập vào sandbox: refresh token xoay vòng sẽ đăng xuất phiên chính.

## Consequences

Tác vụ nền tiêu quota 5 giờ của gói lập trình; chậm hơn API (Claude ~3–7 giây, Codex ~8–12
giây, Antigravity ~16–30 giây mỗi lượt). Bridge phải chạy và CLI phải còn đăng nhập; nếu không,
nhà cung cấp hiện "không phản hồi" và lỗi được phân loại. Rủi ro còn lại: prompt injection có
thể khiến Codex/agy đưa token đăng nhập của chính nó (thứ duy nhất nó thấy) vào kết quả; Claude
Code không có rủi ro này vì không có công cụ.

## Follow-Up

Nếu dùng cho nhóm, cần gói Team/Enterprise hoặc API key thay vì gói cá nhân. Cân nhắc
xdg-dbus-proxy dài hạn và giới hạn quota theo ngày nếu tác vụ nền tiêu quá nhiều.
