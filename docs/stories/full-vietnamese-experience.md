# US-FULL-VIETNAMESE-EXPERIENCE Trải nghiệm sản phẩm hoàn toàn bằng tiếng Việt

## Trạng thái

hoàn tất

## Mức độ

normal

## Cam kết sản phẩm

Các bề mặt do sản phẩm phát hành cho người dùng phải dùng tiếng Việt tự nhiên, rõ nghĩa và nhất
quán. Cách diễn đạt ưu tiên người làm nghiên cứu: đủ chính xác để hiểu đúng nghiệp vụ nhưng tránh
văn phong hàn lâm hoặc dịch từng chữ cứng nhắc.

Các định danh máy cần đọc vẫn giữ nguyên để không phá vỡ hợp đồng kỹ thuật, gồm đường dẫn API, khóa
JSON, mã lỗi, tên biến, tên thư viện, tên nhà cung cấp/mô hình và dữ liệu gốc do người dùng nhập.

## Tài liệu liên quan

- `README.md`
- `Docs/Research System Implementation Plan.md`
- `Docs/Research System Architecture Design.md`
- `Docs/Research System MVP Specification.md`

## Tiêu chí chấp nhận

- Giao diện web chỉ hiển thị tiếng Việt; không còn bộ chuyển EN/VI hoặc mặc định tiếng Anh.
- Tiêu đề trang, điều hướng, trạng thái, nút, gợi ý, lỗi an toàn, nội dung trợ năng và thông báo của
  mọi route chính đều có tiếng Việt phù hợp ngữ cảnh nghiên cứu.
- Thông báo người dùng của API và cổng Discord được Việt hoá mà không đổi mã lỗi, schema hay hành vi.
- README và tài liệu thuật ngữ giải thích rõ nguyên tắc Việt hoá cùng cách dùng thuật ngữ kỹ thuật.
- Kiểm tra tĩnh không phát hiện chuỗi tiếng Anh ngoài danh sách định danh/thuật ngữ được phép; lint,
  typecheck, unit test và build của frontend cùng các test backend/Discord liên quan đều đạt.

## Ghi chú thiết kế

- Không dịch tên riêng và công nghệ: ChatGPT, OpenAI, DeepSeek, GitHub, PostgreSQL, pgvector,
  Meilisearch, Neo4j, MinIO, Ollama, Markdown, PDF, DOCX, LaTeX, RSS, API.
- Dùng các từ quen thuộc khi giúp người nghiên cứu thao tác nhanh: “bản nháp”, “duyệt”, “nguồn”,
  “bằng chứng”, “đồ thị tri thức”, “không gian tài liệu”.
- Với khái niệm khó thay thế hoàn toàn, dùng tiếng Việt trước và thuật ngữ gốc trong ngoặc ở lần giải
  thích đầu tiên; không trộn tiếng Anh tuỳ tiện trong nhãn thao tác.
- Không dịch nội dung nghiên cứu, tiêu đề tài liệu, URL hay dữ liệu lịch sử đã lưu.

## Kiểm chứng

| Lớp | Bằng chứng dự kiến |
| --- | --- |
| Unit | Kiểm tra từ điển tiếng Việt, shell, route và thông báo chính |
| Integration | Test API/Discord liên quan đến thông báo người dùng |
| E2E | Các route chính không còn bộ chuyển ngôn ngữ hoặc nhãn tiếng Anh ngoài danh sách cho phép |
| Platform | Không cần; không đổi runtime hay cấu hình triển khai |
| Release | ESLint, TypeScript, Vitest, build Next.js và kiểm tra tĩnh chuỗi hiển thị |

## Thay đổi Harness

Không thay đổi quy tắc Harness. Story này chỉ ghi lại phạm vi và bằng chứng của yêu cầu Việt hoá.

## Bằng chứng

- Frontend: ESLint, TypeScript, 33 tệp Vitest với 145/145 kiểm thử và bản dựng Next.js 15 route
  đều đạt.
- Backend: Ruff và 323/323 kiểm thử Pytest đạt; chỉ còn cảnh báo tương thích
  Starlette/httpx đã tồn tại từ trước.
- Cổng Discord: Ruff và 55/55 kiểm thử Pytest đạt.
- E2E: 45/45 ca Playwright trên desktop, tablet và mobile đạt cho các luồng ngôn ngữ trọng yếu,
  gồm thư viện/biên tập tài liệu, LaTeX, đồ thị, thay đổi đồ thị, chat, nhập liệu và chân trang.
- Kiểm tra tĩnh từ điển tiếng Việt hiệu lực không phát hiện từ vay mượn bị cấm; kiểm tra cấu trúc
  Markdown, hàng rào mã và `git diff --check` đều đạt.
- Quy ước và thuật ngữ được ghi tại `Docs/Quy uoc ngon ngu tieng Viet.md`; quyết định kiến trúc
  được ghi tại `docs/decisions/0044-vietnamese-only-product-language.md`.
