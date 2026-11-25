# Sửa đồ thị Weave sau audit

## Yêu cầu

Bắt đầu sửa và báo lại năm lỗi audit của bản Weave do OpenCode bàn giao. Intake 23, lane normal,
`US-WEAVE-GRAPH-CANVAS`. Codex, 2026-11-20 +07.

## Tệp và quyết định

- `apps/web/components/document-graph-canvas.tsx`, test tương ứng, route `/documents/[id]` và
  `globals.css`: giới hạn card theo viewBox và ma trận SVG. Quản lý một pointer đang kéo.
  Hủy hoặc mất capture trả vị trí cũ. Sắp xếp lại xóa vị trí kéo. Touch-action kế thừa
  trên phần tử chữ/card để Chrome phân biệt kéo node với cuộn ở phần trống.
- `d3-graph-renderer.ts` và CSS: tọa độ bố cục Quỹ đạo tách khỏi pin do người dùng kéo.
  Hover tôn trọng trạng thái tắt nhãn. Mũi tên được vẽ ở đầu đích của cạnh phân cấp.
- Mở rộng Playwright `document-upload`, `graph-drag`, `graph-hierarchy`; cập nhật story,
  HANDOFF và TASKS.

## Kiểm chứng

- `npm test`, `npm run typecheck`, `npm run lint` trong `apps/web`: 232 tests/45 files, đạt.
- `docker compose restart frontend`: production build đạt và health local `:13000` trả 200.
- Playwright trên `:13000`: `graph-drag`, `graph-hierarchy`, `system-graph`, `viewport-check`,
  ca đồ thị của `document-upload`. Kết quả cuối: 19 đạt, 2 bỏ qua theo cấu hình.
- Lần thử đầu cho thấy Chrome mobile cuộn trang khi chạm text SVG. Probe xác nhận
  `pointercancel`; CSS kế thừa touch-action trên card/text sửa lỗi và lần cuối đạt.
- Harness story complete và `git diff --check` đạt.

## Giới hạn và bước kế tiếp

Kiểm tra touch bằng Chrome mô phỏng, chưa đo fps hoặc nghiệm thu trên thiết bị vật lý.
Linh có thể nghiệm thu UI đã cập nhật tại `http://localhost:13000`.
