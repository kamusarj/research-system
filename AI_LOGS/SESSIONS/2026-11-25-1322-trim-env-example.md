# Rút gọn `.env.example`

## Yêu cầu

Bỏ mục không cần thiết khỏi cấu hình môi trường mẫu. Codex, 2026-11-25 (Asia/Bangkok),
Harness intake 36.

## Tệp thay đổi và quyết định

- `.env.example` giảm từ 245 còn 58 dòng (205 còn 34 biến). Bỏ các dòng lặp mặc định và
  `DATABASE_URL` do Compose ghép từ biến PostgreSQL. Giữ giá trị mẫu khác mặc định và các
  lựa chọn/ô bí mật cần cho lần cài đặt.
- `README.md` trỏ mặc định nâng cao và các giới hạn chat đến `docker-compose.yml`.
- `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và phiên log này lưu tiến độ.
- Phạm vi là cấu hình mẫu Docker cục bộ. `.env`, mẫu triển khai nhóm và cấu hình đang chạy
  được giữ nguyên.

## Lệnh và kiểm chứng

- `scripts/bootstrap-harness.sh`, ghi intake 36 và truy vấn `query matrix --active --summary`.
- So sánh JSON `docker compose --env-file ... config --format json` trước/sau bằng môi trường
  tối thiểu. Kết quả khớp ở Compose cơ sở, toàn bộ profile, lớp phủ multi-user với toàn bộ
  profile và local-ai khi ghi đè cổng/CORS/xác thực. Trình so sánh cũng kiểm tra tên biến duy
  nhất và xác nhận `AUTH_MODE` cho API lẫn worker.
- `git diff --check` đạt.

## Vấn đề còn mở và bước tiếp theo

Việc dọn cấu hình mẫu đã hoàn tất. Hạng mục phát triển tiếp theo vẫn ở bảng công việc hiện hành.
