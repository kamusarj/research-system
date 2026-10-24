# Validation

| Lớp | Bằng chứng |
| --- | --- |
| Unit/integration API | `apps/api`: ruff + 401 pytest (thêm test_worker, test_pipeline_hardening, auth/graph/documents/gaps) |
| Discord | ruff + 55 pytest |
| Frontend | ESLint, `tsc --noEmit`, 180 Vitest (thêm members/account/auth/next-config) |
| Build | `docker build --target runner` (17 route, gồm `/members`, `/account`) |
| E2E triển khai | Stack `bai-teamcheck`: verify, đăng nhập qua proxy, CSRF, phân quyền researcher, đổi mật khẩu, khóa đăng nhập sai, worker dừng 0,3 s exit 0, `db-password`, backup + restore, HTTPS Caddy với cookie Secure |
| Runtime cục bộ | Sao lưu trước, tạo lại container, 7 route 200, 82 nghiên cứu, migration head, `verify_local_autostart.sh` đạt |
