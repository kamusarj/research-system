# Session: Mở Cloudflare quick tunnel để dùng trên điện thoại

## Context

- User request: “hãy chạy project này cho tôi, mở 1 cổng qua cloudflare tunnel để tôi có thể xem
  trên điện thoại và có thể control được”.
- Agent: Claude Code.
- Date/time: 2026-10-23, ~14:10–14:20 Asia/Bangkok (UTC+7).
- Scope: thao tác runtime; không sửa mã nguồn, không đổi cấu hình Compose của repo.

## Work Done

- Runtime cục bộ `businessaiagents` đã chạy sẵn qua autostart (frontend `13000`, API `18000`,
  worker, database đều healthy) nên không khởi động lại.
- Vì local mode dùng `AUTH_MODE=disabled`, thêm cổng mật khẩu trước khi mở ra internet:
  - Container `businessaiagents-tunnel-gate` (image `nginx:alpine` có sẵn), mạng
    `businessaiagents_default`, publish `127.0.0.1:13080:80`, restart `unless-stopped`.
  - nginx basic auth (user `linh`, mật khẩu ngẫu nhiên), proxy tới `frontend:3000`,
    xóa header `Authorization` trước khi chuyển tiếp, tắt buffering, timeout 300 giây,
    `client_max_body_size 200m` cho tải tài liệu.
  - Cấu hình, htpasswd và mật khẩu lưu ở `~/.config/business-ai-agents-tunnel/` (ngoài repo,
    quyền 700); không ghi mật khẩu vào AI_LOGS.
- Tunnel: `systemd-run --user --unit=business-ai-agents-quick-tunnel cloudflared tunnel
  --no-autoupdate --url http://127.0.0.1:13080` (cloudflared 2026.5.2 ở `~/.local/bin`).
- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và session này.

## Reasoning / Decisions

- Quick tunnel (trycloudflare) không cần tài khoản/DNS; phù hợp nhu cầu xem nhanh trên điện thoại.
- Không chuyển sang chế độ nhóm (`make team-up`, đăng nhập thật) vì cần ~8 GB đĩa trống (hiện
  ~4,5 GB) và quyết định `.env.team` của chủ sở hữu; basic auth là lớp bảo vệ tạm tương đương.
- Next.js rewrite `/api/v1/*` sang API nên chỉ cần một tunnel; API chỉ đọc header Bearer nên basic
  auth không xung đột, vẫn xóa header để chắc chắn.
- Dùng transient user unit để tunnel sống độc lập với phiên agent, nhưng không bật lại sau reboot.

## Verification

- Cục bộ `127.0.0.1:13080`: không mật khẩu 401; có mật khẩu `/` 200, `/api/v1/health` 200.
- Log cloudflared: `Registered tunnel connection` (hkg01, quic).
- Qua URL `*.trycloudflare.com`: không mật khẩu 401; `/` 200, `/chat` 200,
  `/api/v1/health` 200 `{"status":"ok"}`.

## Known Issues

- URL quick tunnel đổi mỗi lần khởi động lại unit; unit tạm không tồn tại sau reboot.
- Quick tunnel không có SLA; Cloudflare khuyến nghị dùng named tunnel cho dùng lâu dài.
- Basic auth là một mật khẩu chung; khi dùng cho nhóm nên chuyển sang chế độ nhóm theo
  `Docs/Team Deployment Runbook.md`.

## Next Best Action

- Khi không cần truy cập từ điện thoại: `systemctl --user stop business-ai-agents-quick-tunnel`
  và `docker rm -f businessaiagents-tunnel-gate`.
