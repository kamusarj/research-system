# Design

- Chế độ nhóm là lớp phủ trên `docker-compose.yml` (dùng `!reset`/`!override`) và cùng tên dự án
  Compose, nên dùng lại volume dữ liệu cục bộ. API/worker đặt `DEPLOYMENT_ENVIRONMENT=production`,
  vốn đã buộc `AUTH_MODE=local`, cookie `__Host-` và Secure trong `Settings`.
- Frontend runner là Next standalone; `API_PROXY_TARGET` là build arg vì rewrite được ghi lúc build.
- API không mở cổng nên đặt `FORWARDED_ALLOW_IPS=*` an toàn; vì IP qua Cloudflare có thể giả mạo,
  thêm giới hạn đăng nhập sai theo tài khoản.
- Quyền tự duyệt: chỉ owner hoặc tài khoản dịch vụ (`current_principal_may_publish`).
- Change set: chỉ `draft`/`needs_review` được kiểm tra lại/duyệt/quyết định; khóa hàng với
  `populate_existing`; trùng nút đã lưu trữ báo `ARCHIVED_NODE_EXISTS` ở bước kiểm tra.
- `create_research`/`transition` có `commit=False` để duyệt link/RSS là một giao dịch.
