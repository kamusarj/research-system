# Exec Plan

Status: implemented; acceptance evidence in `validation.md`.

## Goal

Thay API AI bằng quota CLI đăng ký (Codex mặc định, hỗ trợ Claude Code và Antigravity).

## Scope

Cầu nối máy chủ + sandbox, nhà cung cấp `complete_json` và chat đồ thị, cấu hình Compose/
`.env`, systemd user service, UI chat, tài liệu. Không đổi database, không đổi embedding.

## Risk Classification

High-risk: external systems, audit/security (nội dung không tin cậy tới agent CLI), public
contracts (provider id), existing behavior, multi-domain.

## Work Phases

1. Thử headless/structured output của từng CLI và xác định nơi lưu phiên đăng nhập.
2. Viết cầu nối, sandbox bubblewrap, proxy keyring; thử thật từng backend và kiểm tra cô lập.
3. Thêm nhà cung cấp API, chat tool-call bằng JSON, ánh xạ lỗi, UI và cấu hình.
4. Unit test bridge/provider, toàn bộ API test, frontend lint/tsc/test.
5. Cài service, chuyển runtime sang Codex, thử thật từ container, cập nhật log.

## Stop Conditions

Nếu sandbox làm hỏng phiên đăng nhập chính hoặc cần mở cầu nối ra ngoài cổng Docker nội bộ,
dừng và hỏi chủ máy.
