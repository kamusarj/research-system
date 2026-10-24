# US-REBUILD-VIETNAMESE-DOCKER-RUNTIME Build lại runtime Docker tiếng Việt

## Trạng thái

hoàn tất

## Mức độ

normal

## Cam kết sản phẩm

Bốn dịch vụ lõi của Business AI Agents được build từ cây mã hiện tại và chạy lại bằng cấu hình
multi-user đã chấp nhận trên cổng frontend `13000` và API `18000`. Dữ liệu PostgreSQL cùng các
volume có trạng thái phải được giữ nguyên; không tác động tới dự án Smart Exam hoặc các profile tùy
chọn đang tắt.

## Tài liệu liên quan

- `README.md`
- `Docs/Research System Implementation Plan.md`
- `docker-compose.yml`
- `docker-compose.multi-user.yml`

## Tiêu chí chấp nhận

- Build thành công image API/worker và frontend từ cây mã đã Việt hóa.
- Database, API, worker và frontend đều chạy; database, API và frontend đạt healthcheck.
- API trực tiếp, API qua proxy frontend và trang frontend trả HTTP 200.
- Trang frontend đang chạy có nội dung tiếng Việt và tài liệu HTML khai báo `lang="vi"`.
- Migration ở head và kiểm tra bất biến đồ thị đạt.
- Volume PostgreSQL được giữ nguyên; ID container Smart Exam không thay đổi.
- Không khởi động profile Ollama, Meilisearch, Browserless, Neo4j hoặc Discord ngoài phạm vi.

## Ghi chú thiết kế

- Giữ `COMPOSE_PROJECT_NAME=businessaiagents` để gắn lại đúng volume hiện có.
- Dùng lớp phủ `docker-compose.multi-user.yml` giống dịch vụ tự khởi động hiện tại.
- Chỉ dọn build cache không còn dùng khi cần dung lượng; không prune image đang chạy hoặc volume.
- Build image trước khi recreate để giảm thời gian gián đoạn dịch vụ.

## Kiểm chứng

| Lớp | Bằng chứng dự kiến |
| --- | --- |
| Unit | Không cần; không thay đổi mã ứng dụng |
| Integration | Health API trực tiếp/qua proxy, frontend, migration và bất biến đồ thị |
| E2E | Kiểm tra HTTP/HTML tiếng Việt trên runtime thực |
| Platform | Image build, Compose health, bảo toàn volume và container ngoài phạm vi |
| Release | Log khởi động mới không có lỗi nghiêm trọng |

## Thay đổi Harness

Không thay đổi quy tắc Harness; chỉ ghi lại build và bằng chứng runtime.

## Bằng chứng

- Build tuần tự thành công:
  - API: `sha256:0e1adc66ebe254c39c71c909d5fba93fca119555c32e8e705b5640bb038a9dfd`.
  - Worker: `sha256:e820163f6e0c3b6bf7e539c6dfd0922719b7f617e00ad9a98a79f901a2ad13f2`.
  - Frontend: `sha256:7422ab30f4cfe5c7938025ea30e575a3f8e42bf863e6b4d8b9428630ad3eeefe`.
- `docker compose ... up -d --no-build --wait` đạt; database, API và frontend healthy, worker chạy.
- API trực tiếp, API qua proxy và frontend trả HTTP 200; 11 route tĩnh/chính đều trả HTTP 200.
- HTML runtime có `lang="vi"` và thương hiệu “Hệ thống nghiên cứu”.
- Readiness là `ready`; migration `2d4e6f8a0b13 (head)`; đồ thị hợp lệ với 45 nút và 32 cạnh.
- Container database, volume `businessaiagents_postgres_data` và ID hai container Smart Exam không
  thay đổi.
- `scripts/verify_graph_multi_user.sh`, `scripts/verify_local_autostart.sh` và quét log mới đều đạt.
- Cache build không còn dùng đã được dọn; dung lượng trống tăng từ 1,6 GB lên 11 GB mà không xóa
  image đang chạy hoặc volume.
