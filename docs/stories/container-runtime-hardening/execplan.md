# Exec Plan

## Goal

Hoàn tất phần container non-root/mã chỉ đọc đã được chấp nhận trong DEC-064.

## Scope

Dockerfile API, Compose local/team, initializer quyền volume, kiểm thử và hướng dẫn backup/restore.
Không thay schema/credential hay bật tính năng đang tắt. Không xử lý sandbox CLI trong story này.

## Risk Classification

High-risk: audit/security, existing behavior; hard gate security. Harness intake #15,
`US-CONTAINER-RUNTIME-HARDENING`. Hướng đã được chấp nhận tại decision 0051; không cần quyết định
kiến trúc mới từ chủ sở hữu. Decision 0053 ghi lựa chọn thực thi.

## Work Phases

1. Đọc logs, xác nhận runtime/quyền hiện tại và ổ đĩa.
2. Ghi intake/story/decision, triển khai initializer và giới hạn quyền.
3. Chạy test API, cấu hình ba chế độ, canary ảnh cô lập và migration trên DB tạm.
4. Sao lưu DB/tệp, dừng API/worker, áp dụng riêng hai dịch vụ và init.
5. Kiểm tra runtime, dữ liệu, autostart, ghi AI_LOGS và trace.

## Stop Conditions

Không xóa dữ liệu hoặc cache/image để lấy chỗ. Không đổi đăng nhập/AI hay làm yếu kiểm thử.
Nếu thiếu dung lượng build, giữ runtime cũ và ghi rõ giới hạn. Nếu canary lỗi, sửa trước khi áp dụng.
