# Exec Plan

## Goal

Thực hiện các đề xuất audit ngày 2026-11-19 và kiểm tra Mistral thật theo yêu cầu chủ sở hữu.

## Scope and Risk

High-risk: bảo mật đầu ra provider, tính nhất quán backup, hành vi báo cáo, triển khai và đo chi phí.
Giữ PostgreSQL là nguồn chuẩn, báo cáo dạng nháp, các cổng kiểm duyệt và provider mặc định.
Không tải model, xóa dữ liệu, prune tài nguyên dự án khác, đăng ký dịch vụ hay tạo credential giả.

## Work Phases

1. Đọc handoff và ghi intake #19.
2. Sửa grounding/usage/evaluation; local transport/UI; backup/dependencies/CI.
3. Chạy regression, migration PostgreSQL tách biệt và probe Mistral với dữ liệu tổng hợp.
4. Ghi bằng chứng, giới hạn còn lại và bàn giao.

## Stop Conditions

Chỉ hỏi lại nếu cần thay kiến trúc, xóa dữ liệu hoặc cần credential người dùng chưa cung cấp.
Đĩa hạn chế: chỉ dọn cache đã xác định thuộc dự án; không build ảnh lớn khi thiếu dung lượng.
