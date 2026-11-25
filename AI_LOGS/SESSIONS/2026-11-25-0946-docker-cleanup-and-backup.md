# Dọn Docker và xác minh PostgreSQL, sao lưu

## Yêu cầu

Linh yêu cầu dọn Docker và tiếp tục công việc sau audit. Codex xử lý mục dung lượng đang mở
và kiểm chứng lại ghi PostgreSQL, sao lưu, phục vụ giao diện local. Harness intake 27, lane tiny.

## Quyết định và việc đã làm

- Kiểm kê `docker system df -v`, `docker buildx du`, image và container ở mọi trạng thái.
  Gỡ `businessaiagents-ollama-bridge:latest` cũ và `businessaiagents-discord-bot:latest` chưa
  dùng sau khi xác nhận không có container tham chiếu. Cầu nối Ollama đang chạy từ image API.
  Giữ volume, image rollback và tài nguyên các dự án khác.
- Tạo database thử mới trên PostgreSQL local để kiểm chứng volume từng từ chối ghi. Chạy
  migration và test trên database đó, rồi dọn database thử. Không thực hiện migration trên
  database dữ liệu ứng dụng.
- Dùng backup service đã cài. Kiểm tra và xác nhận không có phiên nghiên cứu hay job tiếp
  nhận liên kết đang chạy trước khi engine tạm dừng API/worker. Kiểm bản mới bằng verify-only.

## Tệp thay đổi

`AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và log phiên này.

## Lệnh và kết quả

- `df` và `docker image rm` theo hai tag đã kiểm. Dung lượng Docker khả dụng từ 0 lên 437 MiB,
  còn 437 MiB sau backup. Đã kiểm cả hai tag rollback và bốn volume dự án còn tồn tại.
- `createdb`, `scripts/verify_postgres_migrations.sh`, pytest `test_research_execution_guards.py`
  và `test_pgvector_filter_contract.py`, rồi `dropdb` trên database thử. Migration khứ hồi sạch,
  21 test đạt. Truy vấn catalogue xác nhận không còn database thử của phiên.
- `systemctl --user start business-ai-agents-backup.service` exit 0. Bản `20261125-094606-090959`
  khoảng 5,6 MiB. `scripts/restore_local.py` trả `mode=verified`, kiểm hash, catalogue và 4 tệp
  đính kèm. Timer vẫn hoạt động theo lịch 02:30.
- Sau sao lưu, API/frontend/database báo healthy, worker chạy. `/graph`, `/graph/system` và
  API health 200, API đồ thị ẩn danh 401. `git diff --check` và Markdown đạt.

## Vấn đề còn lại và bước kế tiếp

Dung lượng 437 MiB đủ cho các kiểm tra vừa chạy, cần thêm chỗ cho lần build lớn. Bản local đã sẵn
sàng cho Linh nghiệm thu Weave/Graph v2. Các mục CI GitHub, mô hình thật và KPI token vẫn mở.
