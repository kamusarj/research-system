# Session: Audit tối ưu toàn diện (research / UI / bảo mật) — Bước 0–2

## Context

- User request: tối ưu toàn diện hệ thống research cho nhóm Business AI Agents (chất lượng &
  hiệu năng research, UI/UX, bảo mật). Quy trình yêu cầu: Bước 0 tìm/cài công cụ, Bước 1 audit +
  baseline, Bước 2 trình kế hoạch để duyệt **trước khi sửa code**.
- Agent: Claude Code (Opus 5.5). Date: 2026-10-24 00:20–00:55 Asia/Bangkok.
- Harness: chưa ghi intake (phiên này chỉ audit/lập kế hoạch → read-only theo `AGENTS.md`).

## Work Done

- Files changed:
  - `.claude/settings.json` (mới): bật plugin project-scope `frontend-design` và `claude-security`
    (marketplace chính thức `anthropics/claude-plugins-official`; đã đọc nội dung, không có lệnh
    gửi dữ liệu ra ngoài). Cần `/reload-plugins` để dùng trong phiên.
  - Phiên log này; `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` (một mục mới).
- Không đổi code ứng dụng, container hay dữ liệu.
- Công cụ tạm (scratchpad, ngoài repo): gitleaks 8.30.1 (đã kiểm checksum), Lighthouse 13.5.0,
  pip-audit 2.9.0 (uvx).

## Baseline đo được

- Test: API 460/460 (31 giây), web tsc/eslint sạch, vitest 180/180.
- Thời gian pipeline (lịch sử DB, chỉ đọc): link intake 30 lần hoàn tất, trung vị 12,6 giây,
  TB 14,6 giây, tối đa 70,3 giây; xử lý tài liệu TB 97 giây (2 lần); chat 12 lượt, TB 8,1 giây,
  ~10.400 token vào / ~430 token ra mỗi lượt (ngữ cảnh phình).
- Lighthouse (mobile / desktop): Performance 77–93 / 96–100; Accessibility 94–100 / 94–96;
  LCP mobile 3,2–5,0 giây; CLS `/ingestion` mobile 0,145.
- Secret: gitleaks lịch sử git 0 phát hiện; cây làm việc chỉ có `.env` (đã gitignore, chưa từng
  vào lịch sử) và 2 dương tính giả trong file tracked.
- Dependency: `npm audit --omit=dev` 1 Critical (`next` 15.5.23 → 15.5.28) + 2 High (`sharp`,
  `source-map-js`); pip-audit API: `pypdf` 6.14.2 (22), `pillow` 12.3.0 (35, sửa ở 13.0.0),
  `urllib3` 2.7.0, `certifi`; Discord bot: `aiohttp` 3.14.3, `multidict`.

## Phát hiện chính (chi tiết trong kế hoạch đã trình)

- Bảo mật: cổng 13000/18000 nghe `0.0.0.0` khi `AUTH_MODE=disabled` → ai trong LAN cũng có
  quyền owner, vòng qua cổng mật khẩu tunnel (High); CSRF/DNS rebinding khi tắt đăng nhập; sandbox
  cầu nối CLI rộng (keyring, `auth.json` rw, mạng chung); tự duyệt theo confidence do LLM tự báo;
  container chạy root + mount mã rw; không giới hạn chi phí AI/max_tokens; SSRF TOCTOU DNS; không CSP.
- Research: không có luồng "câu hỏi → báo cáo" (nút nghiên cứu sâu chỉ tạo template); nội dung
  không tin cậy nằm chung chỗ với chỉ dẫn; usage token bị bỏ trong `complete_json`; chat trả tới
  18 đoạn thay vì 6 và lặp; tài liệu gửi 2 lần (40k + 50k ký tự); không cache LLM; trích dẫn link yếu.
- UI: không dark mode/token ngữ nghĩa (247 mã hex rời), không primitive dùng chung/skeleton,
  AuthGate che cả shell, báo cáo hiển thị `<pre>` thô, trích dẫn không bấm được, focus ring mờ.

## Verification

- Chỉ đo/quét, không sửa code. Kết quả lưu ở scratchpad phiên (không vào repo).

## Next Agent Notes

- Continue from: chờ Linh duyệt kế hoạch và trả lời các câu hỏi quyết định (commit baseline
  working tree, nguồn web search, chế độ đăng nhập, ngân sách quota cho eval).
- Watch out for: đĩa còn ~3,7 GB; giữ Next.js 15 (DEC-056), chỉ tiếng Việt (DEC-057), nhận diện
  research workspace (DEC-058); chế độ nhóm tắt cầu nối CLI (DEC-062).
- Suggested next command: `scripts/bootstrap-harness.sh` rồi ghi intake theo `docs/FEATURE_INTAKE.md`
  khi bắt đầu triển khai.
