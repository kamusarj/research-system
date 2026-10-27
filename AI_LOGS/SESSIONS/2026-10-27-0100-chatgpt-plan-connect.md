# Session: Người dùng tự kết nối gói ChatGPT + vòng kiểm thử toàn hệ thống

## Context

- User request: (1) "khi deploy lên web, người dùng tự connect tới Codex để dùng quota tài khoản
  riêng" → chọn hướng 1 (Sign in with ChatGPT + ChatGPT plan usage của OpenAI); (2) goal: "chạy xong
  yêu cầu ở trên rồi chạy loop để test tất cả hệ thống".
- Agent: Claude Code (Opus 5.5). Date: 2026-10-26 → 2026-10-27 Asia/Bangkok.
- Harness: intake #14 high-risk; story `US-CHATGPT-PLAN-CONNECT`; decision 0052 / DEC-065.

## Work Done

- Commits trên `feature/research-system-mvp` (chưa push): `17b8853` API, `55f9156` web, `7c1ccdf`
  docs, `9304c99` sửa sau tự review, cùng các commit của vòng kiểm thử (cấu hình rỗng từ compose,
  thanh công cụ đồ thị, thanh bên màn hình thấp, test E2E đồ thị).
- API: `services/chatgpt_plan.py` (OAuth PKCE + OIDC, mã hóa token, làm mới tuần tự, thu hồi,
  Responses streaming `store=false`), `services/credentials_vault.py` (Fernet, xoay khóa),
  `services/providers/chatgpt_plan_chat.py`, `api/ai_connections.py`, route `/auth/callback`
  (chuyển tiếp loopback), migration `7d9f1b3c5e68` (bảng `ai_plan_connections`,
  `ai_plan_auth_attempts`, cột `document_graph_workspaces.requested_by`), lệnh
  `generate-fernet-key`, lọc mã OAuth khỏi log truy cập; thêm `pyjwt[crypto]`, `cryptography` 50.
- Web: thẻ "Dùng gói ChatGPT của bạn" ở `/account`, trang `/account/ai/callback`, lựa chọn "Gói
  ChatGPT của tôi" trong chat, thông báo lỗi tiếng Việt cho mã `CHATGPT_PLAN_*`.
- Sửa lỗi có từ trước do E2E phát hiện: nút "Khám phá" bị che ở 1280px (thanh công cụ đồ thị theo
  container query); nút Đăng xuất ngoài khung nhìn trên màn hình thấp (menu thanh bên cuộn riêng);
  test bề rộng đồ thị đo theo cột nội dung thay vì cả cửa sổ.
- Runtime (ngoài repo): sao lưu `~/business-ai-agents-backups/pre-chatgpt-plan-*.dump` và
  `env-before-chatgpt-plan-*.bak`; `.env` thêm `CHATGPT_PLAN_ENABLED=true` và
  `CREDENTIALS_ENCRYPTION_KEY` (giá trị không ghi ở đây); ảnh api/worker build lại; migration lên
  `7d9f1b3c5e68`; frontend tạo lại; `nginx -s reload` cổng tunnel.

## Reasoning / Decisions

- Luồng tự đăng ký của OpenAI chỉ cho callback `127.0.0.1` → chế độ cục bộ dùng được ngay từ máy
  chủ; bản web phải chờ OpenAI cấp client ID (form đối tác). Không chọn tải `auth.json` của Codex
  lên máy chủ (không được phép cho ứng dụng web, rủi ro token toàn quyền + Codex chạy lệnh).
- Hoàn tất OAuth trên trang web trong phiên đăng nhập (không ở callback loopback) để `state` gắn
  đúng người bắt đầu, chặn lừa người khác gắn gói của họ vào tài khoản kẻ tấn công.
- Không tự chuyển sang khóa máy chủ khi gói hết hạn mức (yêu cầu của OpenAI). Bỏ ý tưởng cờ "bắt
  buộc gói riêng" vì chưa chặn được lựa chọn nhà cung cấp máy chủ một cách kín kẽ — ghi tồn đọng.

## Verification

- API 570/570 (29 test mới cho gói ChatGPT), ruff sạch; web 199/199 (7 test mới), tsc/eslint sạch,
  `next build` OK; bot 56/56; npm audit 0, pip-audit 0 (API, bot); gitleaks lịch sử 0 (quét thư mục
  chỉ gắn cờ `.env` và cache `.next` — đều bị gitignore).
- Runtime: 44/44 kiểm tra trực tiếp (13 trang, API, plan status/start/bounce, Host lạ 400,
  cross-site 403, CSP, cổng chỉ 127.0.0.1, SearXNG, tunnel); log API/worker không lỗi; preflight
  provider: codex/claude_code/antigravity/deepseek/mistral phản hồi; openai và ollama không.
- Playwright E2E trên stack cô lập (Postgres tmpfs + API/worker riêng cổng 28000 + Next dev 23000,
  khóa Mistral giả): vòng 1 64 qua/14 lỗi; xác nhận lỗi có từ snapshot `dce73d7` bằng worktree; sau
  sửa: 78/78 + 6/6 test đăng nhập (owner/viewer tạm, giới hạn đăng nhập nới riêng cho stack thử).
- Vòng xác nhận cuối trên runtime thật (sau khi đưa bản sửa CSS lên): 44/44 kiểm tra trực tiếp; nút
  "Khám phá" bấm được ở 1280/1366/1440px; cụm tài khoản nằm trong khung nhìn. Lighthouse mobile/desktop
  (Perf/A11y): `/account` 92/100 · 100/100, `/graph` 92/96 · 100/96, `/chat` 79/98 · 99/95 (tồn đọng cũ).
- Stack cô lập, worktree snapshot và dev server tạm đã gỡ sạch.
- Chưa kiểm chứng end-to-end với tài khoản ChatGPT thật (cần Linh đồng ý trên trang OpenAI).

## Next Agent Notes

- Continue from: TASKS "Gói ChatGPT riêng (2026-10-27)".
- Watch out for: `/` chỉ còn ~3–4 GB (build ảnh API từng làm đầy về 0); tạo lại container frontend
  thì `nginx -s reload` cổng tunnel; E2E chỉ chạy trên stack cô lập (bộ test gửi link thật).
- Suggested next command: Linh mở `http://localhost:13000/account` trên chính máy chủ → "Tiếp tục
  với ChatGPT"; sau đó thử một lượt chat với "Gói ChatGPT của tôi".
