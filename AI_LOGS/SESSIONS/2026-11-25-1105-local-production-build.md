# Build Docker API/worker và frontend standalone

## Yêu cầu

Linh hỏi có thể build sau khi dọn Docker và yêu cầu tiếp tục. Harness intake 29, lane tiny.

## Quyết định và tệp thay đổi

- Build từ cây làm việc hiện có, gắn tag local riêng cho hai image. Dùng lại lớp TeX/OCR
  được xác minh để vừa dung lượng đĩa. Frontend dùng Node 22 Alpine và volume dependency
  npm đã xác minh, rồi đóng gói với target `runner` sẵn có.
- Kiểm chứng image với PostgreSQL trên RAM và Docker network nội bộ riêng, không gắn volume
  dữ liệu ứng dụng. Giữ hai image mới để dùng lúc nghiệm thu hoặc triển khai tiếp.
- Cập nhật `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và log phiên này.

## Lệnh và kết quả

- So SHA-256 của `apps/api/uv.lock` với `/app/uv.lock` trong image
  `businessaiagents-api-dependencies:20261103-pypdf-patch`, sau đó `python -m pip check`. Cả hai đạt.
- `docker build --target runtime --build-arg API_DEPENDENCIES_IMAGE=businessaiagents-api-dependencies:20261103-pypdf-patch`
  tạo `businessaiagents-api:local-build-20261125` (ID `90060ed50945`, UID/GID 10001).
- `npm run build` trên host và trong container Node 22 Alpine đạt. `ensure-dependencies.sh`
  xác minh volume khớp. Dùng `docker build --target runner --build-context builder=<đầu ra tạm>`
  tạo `businessaiagents-frontend:local-build-20261125` (ID `334b3d4cba27`, user `web`).
- `API_IMAGE=businessaiagents-api:local-build-20261125 bash scripts/verify_container_hardening.sh`
  đạt kiểm tra Compose, non-root, storage, OCR, LaTeX, migration và đồng bộ schema PostgreSQL.
- Smoke test độc lập: PostgreSQL sẵn sàng, API health 200, worker kiểm tra hàng đợi rỗng thành công.
  Frontend `/graph`, `/graph/system` và tài nguyên JavaScript đều 200. Proxy health 200 và đồ thị
  API ẩn danh 401. Container, network và dữ liệu thử đã được dọn.
- Dung lượng còn khoảng 731 MiB. `git diff --check` và kiểm Markdown đạt.

## Giới hạn và bước kế tiếp

Build dùng dependency có sẵn và hai image mới được kiểm trong môi trường cô lập. Bản local tại
`:13000` đang chạy để Linh nghiệm thu. Build sạch toàn bộ lớp TeX/OCR vẫn cần thêm dung lượng.
