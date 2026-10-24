# Chọn và kiểm tra mô hình API cá nhân

## Current Behavior

API của tôi nhận model dạng text và chỉ phát hiện lỗi khi gửi tin đầu tiên.

## Target Behavior

Nhập key, tải danh sách model trực tiếp, chọn model và chủ động kiểm tra trước khi
kết nối. Lỗi xác thực, credit, hạn mức, quyền truy cập/model, tốc độ và mạng có hướng
xử lý tiếng Việt riêng; lỗi phát sinh khi chat cũng dùng cùng phân loại.

## Affected Users

Researcher/owner; viewer vẫn chỉ đọc. Khóa tạm theo DEC-059, không đổi quyền lịch sử.

## Affected Product Docs

- `README.md`
- `Docs/Research System Implementation Plan.md`
- `docs/decisions/0047-personal-chat-model-validation.md`

## Non-Goals

Lưu khóa, custom endpoint, tự thử model khác, tự nạp tiền, gọi key thật khi kiểm thử.
