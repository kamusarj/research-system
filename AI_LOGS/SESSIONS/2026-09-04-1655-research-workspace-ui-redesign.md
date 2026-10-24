# Session Log

## Context

- User request: thiết kế lại UI của dự án; tiếp tục giữ trải nghiệm tiếng Việt tự nhiên và đưa bản mới vào Docker đang chạy.
- Agent: Codex
- Date/time: 2026-09-04 16:55 +07

## Work Done

- Files changed:
  - `apps/web/components/app-shell.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/lib/i18n.tsx`
  - `apps/web/components/app-shell.test.tsx`
  - `apps/web/e2e/research-workspace.spec.ts`
  - `README.md`
  - `docs/stories/research-workspace-ui-redesign.md`
  - `docs/decisions/0045-research-workspace-ui-redesign.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - `AI_LOGS/DECISIONS.md`
  - `AI_LOGS/SESSIONS/2026-09-04-1655-research-workspace-ui-redesign.md`
- Behavior changed:
  - Desktop chuyển từ top navigation dày sang sidebar xanh đậm, chia hai nhóm “Quy trình nghiên cứu” và “Phân tích và tri thức”.
  - Vùng nội dung desktop có thanh ngữ cảnh, trạng thái hệ thống và lối tắt tìm kiếm; có skip link cho bàn phím.
  - Tablet/mobile tiếp tục truy cập đủ mọi tuyến bằng thanh điều hướng ngang responsive.
  - Token màu, nền, button, form, panel, card, table, page header và dashboard được thiết kế lại theo hướng phẳng, rõ và dễ đọc lâu.
  - API, URL, phân quyền, dữ liệu, graph interaction, document editing và workflow không thay đổi.
  - Chỉ image và container frontend của Business AI Agents được build/recreate; API, worker, PostgreSQL/volume và Smart Exam được giữ nguyên.
- Commands run:
  - `bash scripts/bootstrap-harness.sh`
  - `scripts/bin/harness-cli intake ...`
  - `scripts/bin/harness-cli story add/update/complete ...`
  - `scripts/bin/harness-cli decision add ...`
  - `npm run lint`
  - `npm run typecheck`
  - `npm test -- --run`
  - `npm run build`
  - `E2E_BASE_URL=http://localhost:13001 npx playwright test e2e/research-workspace.spec.ts e2e/viewport-check.spec.ts e2e/shared-footer.spec.ts`
  - `E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/research-workspace.spec.ts --grep "primary workspaces|research desk visual language"`
  - `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml build frontend`
  - `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d --no-build --no-deps --force-recreate frontend`
  - HTTP, Docker health/image/ID, disk, screenshot and visual checks.

## Reasoning / Decisions

- Decision: giữ nhận diện deep-ocean nhưng chuyển cấu trúc sang “research workspace” thay vì thay toàn bộ thương hiệu.
- Reason: sidebar nhóm công việc giúp 10 tuyến dễ quét trên desktop; bề mặt phẳng và nền dịu phù hợp đọc/nghiên cứu lâu hơn, trong khi token dùng chung nâng cấp toàn bộ trang với rủi ro nghiệp vụ thấp.
- Alternatives considered:
  - Chỉ đổi màu/bo góc: không đủ tạo phân cấp mới.
  - Viết lại từng màn hình: rủi ro hồi quy lớn và không cần thiết vì component nghiệp vụ hiện tại đã ổn định.

## Verification

- Tests/checks:
  - ESLint: đạt.
  - TypeScript: đạt.
  - Vitest: 33 tệp, 146/146 kiểm thử đạt; Harness completion chạy lại cùng kết quả.
  - Next.js production build: đạt, 15 route được dựng.
  - Playwright đại diện: hydrate 10 tuyến, visual tokens, intake, draft persistence, footer và graph ở desktop/tablet/mobile đạt. Lượt đầu có 2 lỗi kỳ vọng test cũ về hướng navigation/màu footer; CSS và assertion responsive được sửa, lượt tập trung đạt 3/3.
  - Production runtime smoke: 6/6 ca hydrate/visual đạt trên frontend Docker `13000`; frontend và API auth lần lượt trả HTTP 200.
  - Ảnh trực quan production: dashboard desktop/mobile, thư viện desktop, graph desktop/tablet đều đúng layout; không thấy cuộn ngang ngoài chủ đích.
  - Frontend container healthy và dùng image mới `sha256:380c9413d7d0d35c3d67e09d5d9899aebf1d65423afa8b658aee022ef840a93a`.
  - Smart Exam giữ nguyên bốn container ID: `9a82881f52cc`, `2b2cee9e4c43`, `fe3bb43fe7d3`, `c71296d8f5d4`.
  - Harness decision verification đạt; drift audit không còn mục thiếu và entropy là `0/100`.
- Result: hoàn tất; Harness story `US-RESEARCH-WORKSPACE-UI-REDESIGN` đã complete và standard trace #6 đạt mức yêu cầu cho lane normal.

## Known Issues

- Cần chủ dự án tự xác nhận gu thẩm mỹ và khả năng sử dụng trên màn hình thật; không còn lỗi kỹ thuật đã biết trong phạm vi redesign.
- Ổ hệ thống còn khoảng 9,4 GB sau frontend image build; tránh rebuild API TeX/OCR không cần thiết.

## Next Agent Notes

- Continue from: runtime mới tại `http://localhost:13000` và API tại `http://localhost:18000`.
- Watch out for: breakpoint sidebar là `1181px`; thay đổi app shell phải kiểm tra cả sidebar desktop và navigation ngang tablet/mobile.
- Suggested next command: `cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/research-workspace.spec.ts e2e/viewport-check.spec.ts e2e/shared-footer.spec.ts`.
