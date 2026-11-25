# US-WEAVE-GRAPH-CANVAS Weave-style node canvas for graph diagrams

## Status

done

## Lane

normal

## Product Contract

Các biểu đồ node của hệ thống (Graph tri thức `/graph`, System Map `/graph/system`, Document Graph
trong `/documents/[id]`) dùng chung một ngôn ngữ thiết kế kiểu Figma Weave: node là card bo góc viền
mảnh, dây nối là đường bezier mượt, nền canvas dark theo Weave khi app ở dark mode; light mode giữ
phong cách "giấy" hiện tại nhưng vẫn dùng node/wire thế hệ mới. Kéo thả node tự do ở mọi layout mode,
node bám theo con trỏ realtime 60fps, dây nối cuộn theo trong lúc kéo, kéo xong giữ nguyên vị trí
(không ép force simulation dàn xếp lại); có nút Auto-arrange để sắp xếp tự động lại khi muốn.

## Relevant Product Docs

- `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`
- `docs/decisions/0045-research-workspace-ui-redesign.md`
- `docs/product/` (UI surfaces: graph studio, system map, document workspace)

## Acceptance Criteria

- Node card bo góc (radius ≥ 8px), viền 1px mảnh, fill tối trong dark mode; nhãn đọc được,
  type badge mono in hoa; selected/hover state nổi rõ (viền sáng + shadow nhẹ).
- Mọi cạnh vẽ cubic bezier mượt (không đoạn gấp khúc), stroke mảnh, bo tròn đầu nét; hover cạnh
  làm nổi dây; mũi tên hướng PARENT_OF/BROADER_THAN vẫn đúng.
- Canvas dark có dot grid nhẹ (Weave-style) trong dark mode; zoom/pan mượt (d3.zoom giữ nguyên).
- Kéo thả tự do ở cả relationship, hierarchy và orbit mode: node đi theo con trỏ không trễ,
  chỉ cập nhật node đang kéo + các cạnh liên quan trong lúc kéo (không render lại toàn bộ);
  kéo xong node giữ vị trí; nút Auto-arrange chạy lại layout gốc.
- Node đang kéo có trạng thái "lift" (scale/shadow) và cursor grabbing.
- Document Graph canvas dùng chung style node/wire mới và kéo thả được.
- Không đổi API, schema, dữ liệu; vị trí kéo không persist qua server.
- Keyboard/touch tương tác hiện có (Enter/Space chọn, tab focus) không bị regress; 3 viewport
  (desktop/tablet/mobile) của graph studio vẫn đạt e2e.

## Design Notes

- Commands: không
- Queries: không đổi (`/graph`, `/graph/nodes/{id}/neighbors`, `/graph/system`, `/documents/{id}/graph`)
- API: không đổi
- Tables: không đổi
- Domain rules: không đổi; vị trí node là ephemeral client state
- UI surfaces: `apps/web/app/graph`, `apps/web/app/graph/system`, `apps/web/app/documents/[id]`,
  renderer `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`, styles
  `d3-graph-styles.ts`/`graph-theme.ts`, `apps/web/components/document-graph-canvas.tsx`,
  `apps/web/app/globals.css`

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | vitest cho style/layout/drag helpers mới và các test hiện có vẫn đạt |
| Integration | component tests canvas/toolbar không regress |
| E2E | `viewport-check.spec.ts` + e2e graph hiện có đạt trên 3 viewport |
| Platform | responsive desktop/tablet/mobile |
| Release | `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` đạt |

## Harness Delta

Không thay đổi Harness.

## Evidence

2026-11-20, dev server + runtime thật:

- Unit: vitest **232 passed** (45 file) — gồm `d3-graph-styles.test.ts` (card metrics, bezier, palette,
  theme resolve) và drag test cho Document Graph (pointer drag nuốt click sau kéo).
- Lint/typecheck/build: eslint + tsc sạch; `next build` exit 0.
- E2E Playwright (chrome desktop/tablet/mobile): `graph-hierarchy` + `system-graph` + `viewport-check`
  + `graph-drag` = **16 passed**, 2 skipped-by-design (drag proof chạy desktop một lần). Trong đó:
  viewport-check mock auth/graph để chạy được với `AUTH_MODE=local`; graph-hierarchy cập nhật hợp đồng
  nhãn (luôn hiện trong card) và card `rx=10` thay cho assertion glyph cũ.
- Kéo thả: drag spec chứng minh node bám con trỏ 1:1 (theo zoom scale), dây bezier cuộn theo,
  vị trí giữ qua idle/hover, "Sắp xếp lại" giải phóng pin.
- Theme: screenshot hierarchy/relationship/orbit ở cả light (giấy) và dark (Weave) — dark có
  dot grid, card viền mảnh + accent, badge mono; light giữ màu `#fbfcfe` studio như e2e đã assert.
- Runtime `:13000` đã build lại từ source (frontend restart, health 200); bundle chứa `d3-node-card`.

### Sửa sau audit ngày 2026-11-20 (intake 23)

- Card tài liệu nằm trong viewBox, kể cả khi kéo qua mép. Nút **Sắp xếp lại** đưa các card về
  bố cục ban đầu. Hủy kéo hoặc mất pointer capture trả card về vị trí lúc bắt đầu và giữ lần
  bấm kế tiếp. Chuyển đổi tọa độ theo ma trận SVG và áp dụng touch-action trên cả phần chữ.
- Quỹ đạo tính lại vị trí node theo vòng mới khi resize. Chỉ node từng được kéo giữ vị trí
  ghim. Nút **Sắp xếp lại** giải phóng vị trí ghim.
- Hover trong chế độ Mạng tôn trọng nút **Nhãn**. Cạnh phân cấp dùng đầu mũi tên tại đích.
- Kiểm chứng trên bản production local `:13000`: 232 Vitest, lint, TypeScript, build và health 200.
  Playwright 19 đạt, 2 bỏ qua theo cấu hình chạy ca kéo/quỹ đạo trên desktop. Ca đồ thị tài liệu
  đạt ở desktop, tablet và Chrome mobile với sự kiện cảm ứng mô phỏng.

### Sửa nhãn và kéo thả ngày 2026-11-20 (intake 24)

- **Nhãn** điều khiển chữ trong card, nhãn cụm và lớp chữ của sơ đồ hệ thống. Card phân cấp
  vẫn giữ điều khiển mở nhánh và tên truy cập khi nhãn ẩn. Bật tắt nhãn giữ mức zoom hiện tại.
- Kéo chỉ ghim tọa độ khi con trỏ đã di chuyển. Hủy chạm trả tọa độ ban đầu. Canvas áp dụng
  dữ liệu mới sau khi kết thúc kéo và giữ nguyên mức zoom. Trong chế độ Mạng, kéo chỉ tính lại
  halo cho cụm chứa nút đang kéo.
- Lint, TypeScript, 232 Vitest và production build đạt. Hai trang đồ thị trả 200 tại `:13000`.
  Playwright qua 19 ca đồ thị và 3 ca đồ thị tài liệu trên Chrome desktop, tablet và mobile.
  Hai lượt của ca kéo dành cho desktop được bỏ qua. Chrome mobile dùng cảm ứng mô phỏng.

### Audit lại và khôi phục frontend ngày 2026-11-25 (intake 26)

- Sửa hồi quy build trong lớp vẽ cạnh của intake 25. Cạnh D3 chỉ nhận ID chuỗi hoặc node đã
  ánh xạ. Hàm phân loại cạnh chỉ cần loại và cờ phân cấp phụ. Cạnh có màu nét trở lại ở mọi
  chế độ và cạnh ngữ nghĩa trong Phân cấp nối đến mép card bằng đường cong cubic Bézier.
- Sơ đồ hệ thống đặt nút có liên kết phân cấp phụ bên trong bảng trụ cột đang mở. Bố cục cây
  thông thường vẫn theo cha hiển thị chính. Kiểm tra trình duyệt xác nhận giữ nút được chọn
  khi đổi bố cục, dùng phím mũi tên và Enter trên cạnh, hủy kéo khi chuyển sang chụm hai ngón.
- Production local `/graph` và `/graph/system` trả 200. Lint, TypeScript, build, 236 Vitest,
  55 Playwright và 9 ca đồ thị chạy lại với kiểm tra bàn phím/cảm ứng đạt. Hai lượt của ca kéo
  dành cho desktop được bỏ qua. Browser dùng fixture và Chrome mô phỏng cảm ứng.
