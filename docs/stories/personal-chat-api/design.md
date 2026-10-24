# Design

## Domain Model

ChatSession thêm `credential_source=system|personal`, mặc định system cho lịch sử cũ.
Provider và model của cuộc trò chuyện được lưu như hiện tại. Không có cột khóa.

## Application Flow

React giữ kết nối theo nhà cung cấp trong bộ nhớ, gắn với tài khoản hiện tại. Tạo/nhập
gửi lựa chọn nguồn, mô hình và SecretStr; mỗi lượt chat cá nhân gửi lại khóa vào API
cùng origin. API tạo provider instance với khóa yêu cầu; không sửa global settings.

## Interface Contract

Create/import thêm credential_source, model_name, personal_api_key. Turn chỉ thêm
personal_api_key. Personal thiếu khóa trả CHAT_PERSONAL_KEY_REQUIRED trước khi ghi
tin nhắn; system kèm khóa/mô hình override bị từ chối. Read chỉ trả nguồn khóa.

## Data Model

Migration additive có server default system và check constraint; không sửa hàng cũ
hay thay đổi nội dung/nguồn gốc. Không lưu khóa/token/hash của khóa cá nhân.

## UI / Platform Impact

API của tôi mở biểu mẫu provider/model/password, lưu tạm và xóa khỏi bộ nhớ.
Tạo/nhập chọn nguồn; provider cá nhân có thể dùng dù máy chủ chưa cấu hình provider đó.
Header/composer nêu API cá nhân và hướng nhập lại khi thiếu khóa. Không dùng localStorage.

## Observability

Giữ error envelope đã loại input/ctx/msg, SecretStr/repr masking, payload không ghi log.
Chỉ gọi endpoint HTTPS cố định đã có, không nhận base URL tùy ý.

## Alternatives Considered

Kho khóa mã hóa theo tài khoản cần quyết định lưu lâu dài và quản lý khóa mã hóa riêng;
browser storage plaintext không dùng. Key scope không làm thay đổi governance đồ thị.
