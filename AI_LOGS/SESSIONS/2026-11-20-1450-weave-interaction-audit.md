# Audit nhãn và kéo thả đồ thị Weave

## Yêu cầu

Tiếp tục audit và sửa phần đồ thị Weave sau bàn giao. Intake 24, lane normal,
`US-WEAVE-GRAPH-CANVAS`.

## Tệp và quyết định

- `apps/web/lib/knowledge-graph/d3-graph-renderer.ts` phân biệt nhấp với kéo, khôi phục tọa độ
  khi hủy chạm và chỉ ghim sau khi kéo. Trong thao tác kéo, renderer giữ card và dữ liệu D3
  hiện tại. Khi thả, renderer nạp dữ liệu mới nhất và giữ camera. Chỉ halo của cụm đang kéo
  được tính lại mỗi lần di chuyển.
- `apps/web/components/knowledge-graph/d3-graph-canvas.tsx`, `apps/web/app/graph/system/page.tsx`
  và `apps/web/app/globals.css` cập nhật hiển thị nhãn độc lập với dữ liệu và bố cục.
  Giữ tên truy cập và nút mở nhánh khi ẩn chữ. CSS truyền touch-action xuống phần tử trong card.
- `apps/web/e2e/graph-drag.spec.ts`, `apps/web/e2e/graph-hierarchy.spec.ts` và
  `apps/web/e2e/system-graph.spec.ts` bao phủ bật tắt nhãn, giữ mức zoom, chọn nút trong Quỹ đạo,
  kéo trong lúc đổi bộ lọc và hủy chạm. Cập nhật story, HANDOFF, TASKS và session này.

## Lệnh và kết quả kiểm chứng

- `bash scripts/bootstrap-harness.sh`, intake 24 và truy vấn matrix đã chạy trước khi sửa.
- Playwright trên bản cũ tái hiện nhãn Phân cấp còn hiện, card nhảy khi đổi nhãn giữa lúc kéo
  và thao tác hủy chạm vẫn giữ tọa độ kéo dở. Ca kiểm tra zoom chờ hiệu ứng mở khung kết thúc
  trước khi lưu vị trí camera.
- `npm run lint && npm run typecheck && npm test && npm run build` trong `apps/web` đạt.
  Vitest đạt 232 ca trong 45 tệp. `scripts/bin/harness-cli story complete US-WEAVE-GRAPH-CANVAS` đạt.
- `docker compose restart frontend` nạp code mới. Hai trang `/graph` và `/graph/system`
  trả 200 tại `:13000`. Docker báo frontend và API healthy. API đồ thị yêu cầu đăng nhập
  và trả 401 cho lần kiểm tra HTTP chưa xác thực.
- Playwright trên `:13000` chạy `graph-drag`, `graph-hierarchy`, `system-graph`,
  `viewport-check` và ca `processed document exposes` của `document-upload`. Tổng 22 ca
  đạt và 2 lượt bỏ qua theo cấu hình. `git diff --check` đạt.

## Giới hạn và bước kế tiếp

Ca trình duyệt dùng dữ liệu fixture và Chrome mobile mô phỏng cảm ứng. Nghiệm thu thao tác kéo
trên thiết bị cảm ứng thật khi có thiết bị.
