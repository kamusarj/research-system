# Dọn cache Docker BuildKit toàn máy

## Yêu cầu

Linh yêu cầu dọn cả cache build của các dự án khác. Harness intake 28, lane tiny.

## Quyết định và tệp thay đổi

Chỉ dùng thao tác dọn cache BuildKit trên builder `default`, builder duy nhất trong Docker context
local. `--all` bao gồm cache nội bộ/frontend của BuildKit. Đối chiếu danh mục Docker trước và sau.
Cập nhật `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và log phiên này.

## Lệnh và kiểm chứng

- `docker buildx ls`, `docker system df`, `df`, rồi `docker buildx prune --builder default --all --force`.
- `docker buildx du --builder default` và `docker system df` xác nhận cache còn 0 B. BuildKit báo
  dọn 1,097 GB cache. Trên filesystem, dung lượng khả dụng từ 435,9 lên 1.199,4 MiB, thêm 763,5 MiB.
- Danh mục image (ID và tag), container (ID và tên) và volume (tên) trước/sau khớp.
- API health và trang `/graph` trả HTTP 200. Kiểm `git diff --check` và Markdown đạt.

## Vấn đề còn lại và bước kế tiếp

Các lần build tới sẽ tạo cache lại. Bản local sẵn sàng cho Linh nghiệm thu Weave/Graph v2.
