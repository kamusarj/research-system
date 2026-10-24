# US-RESEARCH-WORKSPACE-UI-REDESIGN Thiết kế lại không gian làm việc nghiên cứu

## Status

implemented

## Lane

normal

## Product Contract

Toàn bộ sản phẩm nghiên cứu phải có một ngôn ngữ thị giác thống nhất, hiện đại và dễ đọc trong thời gian dài. Giao diện chỉ dùng tiếng Việt tự nhiên, giữ nguyên hợp đồng API, quyền truy cập, URL và hành vi nghiệp vụ hiện có.

## Relevant Product Docs

- `Docs/Research System Implementation Plan.md`
- `Docs/Quy uoc ngon ngu tieng Viet.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/decisions/0044-vietnamese-only-product-language.md`

## Acceptance Criteria

- Khung ứng dụng, trang tổng quan và các bề mặt dùng chung tạo thành một không gian làm việc nghiên cứu mạch lạc với phân cấp thông tin rõ ràng.
- Tất cả tuyến hiện có tiếp tục truy cập được; thao tác, trạng thái, phân quyền và hợp đồng API không thay đổi.
- Nội dung người dùng nhìn thấy chỉ dùng tiếng Việt tự nhiên và nhất quán.
- Giao diện hoạt động tốt ở kích thước desktop, tablet và mobile, không xuất hiện cuộn ngang ngoài chủ đích.
- Trạng thái focus, độ tương phản, vùng bấm và thiết lập giảm chuyển động đáp ứng nhu cầu truy cập cơ bản.
- Kiểm thử đơn vị, lint, typecheck, build và bộ E2E giao diện đại diện đều vượt qua.
- Chỉ dịch vụ frontend Docker được build/recreate; API, cơ sở dữ liệu và Smart Exam không bị thay đổi.

## Design Notes

- Commands: không thay đổi.
- Queries: không thay đổi.
- API: không thay đổi.
- Tables: không thay đổi.
- Domain rules: không thay đổi.
- UI surfaces: app shell, dashboard, form, table, panel, editor, graph, chat, trạng thái rỗng và responsive navigation.

Thiết kế mới theo hướng “research workspace”: nền giấy dịu để đọc lâu, thanh điều hướng xanh đậm, điểm nhấn teal, bề mặt ít bóng đổ, nhịp khoảng cách rõ và dữ liệu được ưu tiên hơn trang trí.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Toàn bộ Vitest frontend vượt qua. |
| Integration | Lint, typecheck và production build vượt qua. |
| E2E | Các luồng giao diện và responsive đại diện vượt qua trên Chromium. |
| Platform | Frontend Docker được build/recreate và phản hồi HTTP thành công. |
| Release | Kiểm tra trực quan các tuyến chính ở desktop và mobile. |

## Harness Delta

Không cần thay đổi Harness; story và decision record lưu lại hợp đồng thiết kế mới.

## Evidence

- `npm run lint`: đạt.
- `npm run typecheck`: đạt.
- `npm test -- --run`: 33 tệp / 146 kiểm thử đạt.
- `npm run build`: production build Next.js đạt trên 15 route.
- Playwright đại diện: hydrate 10 tuyến, token thiết kế, intake, draft persistence, footer và graph desktop/tablet/mobile đều đạt; lỗi kỳ vọng màu footer cũ ở lượt đầu đã được sửa và test ba viewport đạt 3/3.
- Runtime Docker mới: frontend `13000` và API auth `18000` trả HTTP 200; frontend container healthy và dùng đúng image mới.
- Smoke test trực tiếp trên production container: 6/6 ca hydrate/visual ở desktop, tablet và mobile đạt.
- Kiểm tra trực quan: dashboard, thư viện và graph ở desktop; dashboard mobile và graph tablet không có va chạm layout hoặc cuộn ngang ngoài chủ đích.
- API, database, worker và bốn container Smart Exam không bị recreate trong đợt thay đổi frontend này.
- Harness completion, decision verification, standard trace #6 và audit entropy `0/100` đạt.
- Phần hệ thống thiết kế trong `README.md` đã được cập nhật theo breakpoint và token mới.
