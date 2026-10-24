# Design

## Domain Model

Model list chỉ chứng minh key đọc được danh mục, không chứng minh credit hoặc khả
năng dùng endpoint chat. Kết nối chỉ lưu trong React sau khi probe model thành công.

## Application Flow

POST models dùng key yêu cầu với HTTPS cố định. POST verify gọi đúng adapter đang
dùng cho chat, prompt tổng hợp và tool vô hại, giới hạn 16 token đầu ra/20 giây,
không thực thi tool hay gửi dữ liệu nghiên cứu. Không retry/fallback. Hủy/bỏ qua kết
quả cũ khi thay key/provider/model, đóng form hoặc đổi tài khoản.

## Interface Contract

`POST /chat/connections/models`: provider + personal_api_key, trả provider/models.
`POST /chat/connections/verify`: thêm model_name, trả provider/model_name/verified.
SecretStr bắt buộc, không có trường chứa key trong response. Auth/CSRF như chat POST,
rate bucket chung cho hai endpoint. Lỗi upstream chuyển thành mã cố định an toàn.

## Data Model

Không thay schema, không ghi session/message/audit payload hoặc cache credential.

## UI / Platform Impact

Model select có trạng thái chưa tải/đang tải/rỗng/lỗi. Không save khi probe lỗi.
Mô hình cuộc trò chuyện cũ được giữ và kiểm tra riêng khi nhập lại key.

## Observability

Không echo upstream body/message hoặc headers. Giữ redaction validation hiện có;
response kết nối no-store. Success chỉ có nghĩa thành công tại thời điểm kiểm tra.

## Alternatives Considered

Danh mục hardcode dễ cũ; suy credit từ model list không đáng tin. Không bổ sung API
số dư riêng vì probe thực tế đã kiểm tra khả năng thực hiện và không lộ tài chính.
