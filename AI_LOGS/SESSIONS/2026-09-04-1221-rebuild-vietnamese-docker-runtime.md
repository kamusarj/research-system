# Nhật ký phiên làm việc

## Bối cảnh

- Yêu cầu của người dùng: Build lại Docker cho dự án sau khi hoàn tất Việt hóa.
- Agent: Codex
- Ngày/giờ: 2026-09-04 12:21 +07

## Công việc đã làm

- Tệp đã thay đổi:
  - `docs/stories/rebuild-vietnamese-docker-runtime.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - `AI_LOGS/SESSIONS/2026-09-04-1221-rebuild-vietnamese-docker-runtime.md`
- Không thay đổi mã ứng dụng, Compose, migration hoặc dữ liệu.
- Hành vi đã thay đổi:
  - Build image API, worker và frontend từ cây mã hiện tại.
  - Recreate API, worker và frontend bằng cấu hình multi-user; giữ nguyên database container và
    volume `businessaiagents_postgres_data`.
  - Giữ nguyên project Compose `businessaiagents`, cổng API `18000` và frontend `13000`.
  - Không khởi động hoặc thay đổi các profile Ollama, Meilisearch, Browserless, Neo4j và Discord.
- Lệnh đã chạy:
  - Startup protocol và `bash scripts/bootstrap-harness.sh`.
  - Harness intake #5, story add/update/verify/complete và truy vấn ma trận.
  - `docker builder prune --force` chỉ cho cache build không còn dùng.
  - `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml build` cho API, worker
    và frontend.
  - `docker compose ... up -d --no-build --force-recreate api worker frontend` rồi `--wait`.
  - Kiểm tra `docker compose ps`, `docker inspect`, HTTP routes, readiness, Alembic, bất biến đồ thị,
    log mới, dung lượng đĩa, autostart và cấu hình multi-user.

## Lập luận và quyết định

- Quyết định: build image trước khi recreate để runtime cũ tiếp tục phục vụ trong phần lớn thời gian.
- Lý do: người dùng yêu cầu build lại, nhưng dữ liệu PostgreSQL và dự án Smart Exam phải được giữ
  nguyên.
- Phương án đã cân nhắc:
  - Build đồng thời ba image theo Compose: lượt đầu hoàn tất phần build nhưng lỗi khi giải nén đồng
    thời API/worker do thiếu dung lượng.
  - Build tuần tự API, worker rồi frontend: được chọn; worker dùng lại lớp cache giống API và cả ba
    image hoàn tất thành công.
  - Xóa volume hoặc image đang chạy: không thực hiện vì không cần thiết và có nguy cơ mất dữ liệu.

## Kiểm chứng

- Image cuối:
  - API: `sha256:0e1adc66ebe254c39c71c909d5fba93fca119555c32e8e705b5640bb038a9dfd`.
  - Worker: `sha256:e820163f6e0c3b6bf7e539c6dfd0922719b7f617e00ad9a98a79f901a2ad13f2`.
  - Frontend: `sha256:7422ab30f4cfe5c7938025ea30e575a3f8e42bf863e6b4d8b9428630ad3eeefe`.
- API trực tiếp, API qua proxy và frontend: HTTP 200.
- 11 route chính: 11/11 HTTP 200.
- HTML runtime: `lang="vi"` và có “Hệ thống nghiên cứu”.
- Readiness: `ready`; graph 45 nút / 32 cạnh, không lỗi.
- Migration: `2d4e6f8a0b13 (head)`.
- `scripts/verify_graph_multi_user.sh`: đạt với 4 API worker và pool database có giới hạn.
- `scripts/verify_local_autostart.sh`: đạt.
- Log mới: không có traceback, exception, fatal, unhandled, lỗi hết chỗ hoặc `error:`.
- Bảo toàn: database container ID, PostgreSQL volume và ID `smart_exam_backend` /
  `smart_exam_frontend` không đổi.
- Dung lượng: từ 1,6 GB trống / 98% sử dụng lên 11 GB trống / 83% sử dụng; không xóa volume hay
  image đang chạy.
- Kết quả: đạt; Harness story đã ở trạng thái `implemented`; detailed trace #5 đạt 3/3.

## Vấn đề đã biết

- Worker không có healthcheck riêng trong Compose; trạng thái chạy và log khởi động sạch đã được
  kiểm tra. API, frontend và database đều healthy.
- Ổ hệ thống vẫn nên được theo dõi vì image TeX/OCR tạo lớp build lớn, dù hiện còn 11 GB trống.

## Ghi chú cho phiên tiếp theo

- Tiếp tục từ: frontend tiếng Việt đang chạy tại `http://localhost:13000`; API tại
  `http://localhost:18000`.
- Lưu ý: giữ `COMPOSE_PROJECT_NAME=businessaiagents` và hai lớp Compose khi vận hành thủ công để
  không tách khỏi volume/runtime tự khởi động hiện tại.
- Lệnh tiếp theo được đề xuất: `scripts/verify_local_autostart.sh` nếu cần kiểm tra lại sau lần khởi
  động máy tiếp theo.
