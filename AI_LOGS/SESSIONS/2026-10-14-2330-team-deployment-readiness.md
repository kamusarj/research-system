# Session Log — Rà soát luồng và sẵn sàng triển khai cho nhóm

## Context

- User request: đọc repo, kiểm tra các luồng hoạt động, tự refactor những gì chưa hợp lý (được dùng
  skill/subagent), báo cáo để dự án sẵn sàng deploy cho thành viên nhóm nghiên cứu.
- Agent: Claude Code (Opus 5.5), 2026-10-14.
- Harness: intake #10 (high-risk), story `US-TEAM-DEPLOYMENT-READINESS`, DEC-061 / decision 0048.

## Work Done

- Ba subagent rà soát chỉ đọc (pipeline/worker, đồ thị/chat/search/auth, frontend); xác minh lại
  từng phát hiện trước khi sửa.
- Hạ tầng: `docker-compose.yml` (anchor môi trường chung API/worker — worker trước đó thiếu 83 biến
  gồm embedding/RAG; mật khẩu DB tham số hóa; `init: true`; frontend `target: dev`),
  `docker-compose.team.yml`, `.env.team.example`, `scripts/team.sh`, Makefile `team-*`,
  `apps/web/Dockerfile` nhiều stage (runner standalone không root), `.dockerignore`,
  `scripts/start_local_autostart.sh` + `verify_local_autostart.sh` nhận chế độ nhóm, `.gitignore`.
- Backend: phân quyền (`core/auth.py`, `core/identity.py`, `api/research.py`, `intake_receipts.py`),
  change set (`graph_changes.py`), duyệt nguyên tử + khóa (`ingestion.py`, `research.py`,
  `collector.py`), lease tối đa (`ingestion.py`, `document_processing.py`), hạn tổng tải nguồn
  (`sources/http.py`), robots/GitHub có giới hạn, RSS qua `fetch_public`, inline chỉ PDF + CSP
  (`api/documents.py`), xóa tài liệu commit trước, giải phóng kết nối khi gọi AI (`graph_chat.py`,
  `ai.py`) + mã lỗi AI có kiểu, rate limit theo người dùng + route AI/semantic, khóa đăng nhập sai
  theo tài khoản, đổi mật khẩu tự phục vụ, xóa cookie `__Host-` đúng cách, khoảng trống hết hạn hoãn,
  change set chat ghi người tạo, worker dừng an toàn bằng SIGTERM, giới hạn `/ingestion/links`,
  `offset` cho `/documents`, xóa mã chết.
- Frontend: xử lý hết phiên/401, xác nhận cookie sau đăng nhập, đăng xuất an toàn, không retry 4xx,
  thông báo lỗi theo trạng thái, phân trang (thư viện + tab lưu trữ, tìm kiếm, tài liệu), lỗi thao tác
  (chi tiết nghiên cứu, AI panel, khoảng trống, RSS), form không ghi đè gợi ý AI, nhập URL giữ đúng
  link lỗi, CTA theo quyền, security headers, trang `/members` và `/account`, nhóm điều hướng Quản trị.
- Tài liệu: `Docs/Team Deployment Runbook.md`, README, story packet và decision 0048.

## Reasoning / Decisions

- Lớp phủ thay vì file production riêng để không nhân đôi ~150 biến môi trường.
- Ảnh kiểm thử API dựng mỏng từ ảnh cũ (pyproject không đổi) vì đĩa chỉ còn ~3 GB, không đủ build
  lại lớp TeX ~4,5 GB; `make team-up` sẽ build đầy đủ.
- Không đổi chuẩn hóa khóa tiếng Việt và không tiêu thụ `outbox_events` (cần migration/quyết định).

## Verification

- API: ruff + 401 pytest; Discord: ruff + 55; frontend: ESLint, tsc, 180 Vitest; verify_migrations.
- Docker: build `runner` (17 route); stack cô lập `bai-teamcheck` đạt verify, đăng nhập qua proxy,
  CSRF, quyền researcher (bulk-review/users 403, auto_approve bị bỏ), đổi mật khẩu, khóa đăng nhập
  sai (429), worker dừng 0,3 s exit 0, `db-password`, backup + restore, HTTPS Caddy + cookie Secure,
  HTTP→HTTPS 308. Đã gỡ stack, volume, ảnh và build cache của phiên.
- Runtime cục bộ: sao lưu `~/business-ai-agents-backups/*-before-team-refactor`, tạo lại
  API/worker/DB, rebuild frontend; 7 route 200, 82 nghiên cứu, migration `3e5f7a9b1c24 (head)`,
  readiness `ready`; cài lại script autostart, `verify_local_autostart.sh` đạt.

## Next Agent Notes

- Chủ sở hữu cần: tạo `.env.team`, chọn lối vào HTTPS, chạy `make team-up` (cần ~8 GB đĩa trống),
  `make team-owner`, thêm thành viên ở `/members`, lên lịch `make team-backup`.
- Chưa commit: toàn bộ thay đổi vẫn nằm trong working tree (repo chỉ có 1 commit ban đầu).
- Theo dõi: chuẩn hóa khóa tiếng Việt, `outbox_events`, rate limit/metrics theo tiến trình.
