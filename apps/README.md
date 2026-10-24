# Các ứng dụng

Toàn bộ mã ứng dụng có thể triển khai nằm trong thư mục này.

## Mô-đun

- `api/`: dịch vụ FastAPI. Bộ định tuyến HTTP nằm trong `app/api`, logic nghiệp vụ/ứng dụng trong `app/services`, hợp đồng yêu cầu/phản hồi trong `app/schemas`, lớp lưu trữ trong `app/models.py` và `migrations/`.
- `web/`: ứng dụng Next.js App Router. Các trang nằm trong `app`, thành phần giao diện tái sử dụng trong `components`, hợp đồng API và hàm hỗ trợ phía khách trong `lib`.

## Chiều phụ thuộc

```text
web -> /api/v1 HTTP contract -> api -> PostgreSQL
```

Ứng dụng web không nhập phần nội bộ của API. Tìm kiếm và đồ thị là các bản chiếu có thể dựng lại từ cơ sở dữ liệu chính của API. Cấu hình điều phối dùng chung vẫn ở thư mục gốc để `docker compose` và `make` là các điểm vào ổn định.

## Quy ước đặt tên

Dùng tên dịch vụ triển khai được (`api`, `web`) cho thư mục và dịch vụ Compose. Đặt thành phần triển khai mới như worker trong `apps/`; chỉ tạo mã dùng chung không triển khai trong thư mục gốc `packages/` khi thực sự có nhu cầu tái sử dụng giữa các ứng dụng.
