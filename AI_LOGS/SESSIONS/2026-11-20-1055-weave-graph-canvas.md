# Session Log — Weave-style graph canvas (US-WEAVE-GRAPH-CANVAS)

## Context

- User request: thiết kế các biểu đồ theo phong cách weave.figma.com (Figma Weave), kéo thả mượt
  như Weave. Đã hỏi chốt phạm vi: tất cả biểu đồ node (graph, system map, document graph),
  kéo thả tự do kiểu Weave + auto-arrange, dark theo Weave / light giữ phong cách "giấy".
- Agent: OpenCode; intake #22, lane normal, story `US-WEAVE-GRAPH-CANVAS`.
- Date/time: 2026-11-20 10:55 +07.

## Files Changed

- `apps/web/lib/knowledge-graph/d3-graph-styles.ts`: palette Weave (light/dark), `nodeCardMetrics`,
  `nodeCardWidth`, `edgeBezierPath`, `cardEdgePath`, `resolveCanvasTheme`.
- `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`: node card bo góc + accent + badge mono cho
  relationship/orbit; edge bezier mọi mode (fix luôn bug orbit edge dùng string id); free-drag
  mọi layout (chỉ repaint node kéo + cạnh liên quan, kéo xong pin vị trí); relayout = auto-arrange
  giải phóng pin; theme-aware theo `data-theme`/matchMedia; vị trí giữ qua setData refresh.
- `apps/web/components/document-graph-canvas.tsx`: edge bezier (dọc cho contains, ngang cho
  semantic), card accent, pointer drag (rAF batched, nuốt click sau kéo, giữ vị trí).
- `apps/web/app/globals.css`: style card/dragging; block Weave-dark cho graph-studio (dot grid,
  chrome tối) cả `data-theme` lẫn media fallback; document-graph path/đổi theme.
- `apps/web/e2e/graph-hierarchy.spec.ts`: hợp đồng mới — card `rx=10`, nhãn luôn hiện trong card
  (14/14), edge resting opacity 0.3.
- `apps/web/e2e/viewport-check.spec.ts`: mock auth+graph (chạy được với `AUTH_MODE=local`),
  fixture có `PARENT_OF` edges (hierarchy projection yêu cầu), screenshot path `testInfo.outputPath`.
- `apps/web/e2e/graph-drag.spec.ts` (mới): proof kéo thả tự do.
- `apps/web/lib/knowledge-graph/d3-graph-styles.test.ts` (mới), `document-graph-canvas.test.tsx`
  (thêm drag case). `apps/web/scripts/weave-screenshots.ts` (tooling chụp minh chứng).
- `docs/stories/weave-graph-canvas.md` (story packet + evidence).

## Decisions made

- Node unified thành Weave card (rounded rect, viền mảnh, accent bar theo type, badge mono in hoa,
  nhãn nằm trong card) thay cho glyph circle/diamond/rect; mọi edge là cubic bezier mượt.
- Nhãn LUÔN hiện trong card ở relationship mode (Weave identity); toggle "Nhãn" là công tắc duy
  nhất; focus dimming bằng group opacity. Cạnh giữ "lặng khi nghỉ" nhưng nâng 0.08→0.3 cho thấy
  dây nối như Weave.
- Kéo thả tự do mọi mode: không restart simulation, không render lại toàn bộ khi kéo; kéo xong
  pin `fx/fy` để giữ vị trí qua refresh/resize; "Sắp xếp lại" (relayout) giải phóng pin.
- Collision force dùng bề rộng card (`nodeCardWidth`) — card rộng ~200px cần bán kính va chạm
  theo bề rộng, không thì card chồng nhau (đã bắt bằng e2e mobile fail).
- Theme: dark = Weave (#17171b + dot grid, card #202027 viền rgba trắng), light = giữ nguyên màu
  "tờ giấy" (e2e assert nền `rgb(251,252,254)` — không đổi). Renderer tự đổi màu theo
  `data-theme`/matchMedia, không cần remount.
- Không đổi API/schema/dữ liệu; vị trí kéo ephemeral (không persist server).

## Commands / Verification

```text
cd apps/web
npm test            # 232 passed (45 files)
npm run lint        # clean
npm run typecheck   # clean
npm run build       # exit 0
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/graph-hierarchy.spec.ts e2e/system-graph.spec.ts e2e/viewport-check.spec.ts e2e/graph-drag.spec.ts   # 16 passed, 2 skipped-by-design
```

- `harness-cli story complete US-WEAVE-GRAPH-CANVAS` = pass.
- Screenshot light+dark (hierarchy/relationship/orbit) đã xem tay: dark đúng ngôn ngữ Weave
  (dot grid, card viền mảnh, badge mono, halo cụm); light giữ giấy. Runtime `:13000` build lại
  từ source (frontend restart, healthy), bundle chứa `d3-node-card`.

## Known Issues / Limits

- Vị trí kéo không persist qua reload (hợp đồng đã chọn); có nút "Sắp xếp lại".
- Zoom controls icon nhỏ (10px, hành vi cũ) — không thuộc scope.
- Đĩa root vẫn chặt (~560MB); frontend build trong container đã chạy ổn nhưng không build thêm.
- Dark mode của các trang khác (dashboard, documents) giữ nguyên — chỉ graph studio/document graph
  theo Weave-dark.

## Next Best Action

Linh nghiệm thu UI Weave trên :13000 (graph, system map, document graph; kéo thả; dark/light).
Nếu duyệt: Linh quyết commit/push (cùng CI workflow đang chờ). Tiếp theo tùy ưu tiên: đo lại
paired eval khi hạn mức Codex reset, hoặc tinh chỉnh visual Weave (width curve, minimap...).
