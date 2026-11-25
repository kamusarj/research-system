# Dọn image Docker của ba dự án

## Yêu cầu

Linh yêu cầu dọn ba nhóm image vừa được xác định có thể thu hồi thuộc Deka, Smart Exam và
Cineforge. Harness intake 31, lane tiny.

## Tệp thay đổi và quyết định

- Dọn theo danh sách tag, chỉ gỡ khi kiểm cả container chạy và container dừng đều không
  tham chiếu image. Không dùng `--force`.
- Proxy Deka đang chạy. Đối chiếu chỉ các biến tên image từ cấu hình và giữ bộ Deka private
  đang cấu hình, gồm PostgreSQL và ClamAV, cùng các tag rollback.
- Xác minh ChromaDB có thể tải lại từ registry theo digest
  `chromadb/chroma@sha256:1e0b73a187a28757c572acba508c46f48c9e8b0acaf5c20e6d95cdedce1acdf6`.
- Cập nhật `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và log phiên này.

## Lệnh và kết quả

- `docker image rm` gỡ Deka `deka-backend:eval-local`; Smart Exam `smart-exam-ai-backend:latest`,
  `smart-exam-ai-frontend:latest`, `smart-exam-frontend-new:latest` và `chromadb/chroma:latest`;
  Cineforge `cineforge-web:latest` và `cineforge-api:phase0`.
- `df -B1` đo dung lượng khả dụng từ 5.306.396.672 B lên 8.896.843.776 B, tăng 3,59 GB.
  Docker còn 27 image, 15 container, 40 volume và cache BuildKit 0 B.
- Danh mục container (ID, tên, trạng thái và tham chiếu image) và volume khớp trước/sau.
  Proxy Deka chạy, API health và frontend Business AI Agents trả 200.
- `git diff --check` và kiểm Markdown đạt.

## Vấn đề còn lại và bước kế tiếp

Các image phát triển đã gỡ cần build hoặc tải lại khi dự án tương ứng được chạy lại. Dữ liệu
của chúng vẫn ở các volume hiện có. Bản Business AI Agents tại `:13000` sẵn sàng nghiệm thu.
