# 0048 Team deployment overlay and owner-only publish gates

Date: 2026-10-14

## Status

Accepted

## Context

Chủ sở hữu muốn triển khai cho thành viên nhóm nghiên cứu. Chế độ hiện tại là cục bộ không đăng
nhập; rà soát phát hiện các đường vòng cho phép nhà nghiên cứu xuất bản mà không qua chủ sở hữu và
các giới hạn tần suất dùng chung một IP proxy.

## Decision

- Thêm lớp phủ `docker-compose.team.yml` (production, đăng nhập bắt buộc, API không mở cổng, HTTPS
  qua Caddy/Cloudflare Tunnel) cùng `.env.team`, `scripts/team.sh` và `make team-*`.
- Mọi thao tác xuất bản/duyệt (kể cả duyệt hàng loạt, quyết định mutation, cấu hình nguồn RSS) chỉ
  dành cho owner; yêu cầu tự duyệt chỉ có hiệu lực với owner hoặc tài khoản dịch vụ; nhà nghiên cứu
  không sửa nghiên cứu `in-review`/`approved`.
- Giới hạn tần suất theo tài khoản; đăng nhập sai giới hạn theo tài khoản và IP thật.
- Thành viên tự đổi mật khẩu (`POST /auth/me/password`); owner quản lý tài khoản ở `/members`.

## Alternatives Considered

1. File Compose production độc lập: trùng lặp ~150 biến môi trường, dễ lệch với bản cục bộ.
2. Đưa nội dung đã duyệt về `draft` khi nhà nghiên cứu sửa: làm mục biến mất khỏi tìm kiếm/đồ thị.

## Consequences

Positive:

- Một lệnh dựng bản nhóm, dùng lại dữ liệu cục bộ; quyền xuất bản nhất quán ở API.

Tradeoffs:

- Nhà nghiên cứu cần chủ sở hữu duyệt/sửa nội dung đã xuất bản; giới hạn vẫn theo tiến trình.

## Follow-Up

- Quyết định chuẩn hóa khóa tiếng Việt (migration dữ liệu), tiêu thụ `outbox_events`, rate limit dùng chung.
