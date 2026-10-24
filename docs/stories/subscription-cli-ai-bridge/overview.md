# Dùng quota CLI đăng ký thay cho API AI

## Current Behavior

Mọi tác vụ AI gọi API trả phí (Mistral cho tác vụ JSON, DeepSeek cho chat) bằng khóa máy chủ.

## Target Behavior

Chủ máy chọn `claude_code`, `codex` hoặc `antigravity` làm nhà cung cấp cho phân loại link, xử
lý tài liệu, paper-fit, trích xuất đồ thị, sửa tài liệu, brainstorm và chat đồ thị có công cụ.
Lời gọi đi qua cầu nối trên máy chủ dùng phiên đăng nhập gói đăng ký của CLI. Runtime cục bộ
mặc định Codex (`gpt-6-luna`, effort thấp). Embedding vẫn dùng Mistral.

## Affected Users

Owner/researcher ở chế độ cục bộ. Chế độ nhóm không dùng được (cầu nối luôn tắt).

## Affected Product Docs

- `README.md`
- `docs/decisions/0049-subscription-cli-ai-bridge.md`
- `AI_LOGS/DECISIONS.md` (DEC-062)

## Non-Goals

Embedding qua CLI, API key cá nhân cho CLI, chế độ nhóm dùng gói cá nhân, streaming token,
tự chọn model CLI trong UI (cấu hình qua `.env`).
