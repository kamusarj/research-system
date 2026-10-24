# US-AI-CHAT-REDESIGN Thiết kế lại trò chuyện AI

## Status

implemented

## Lane

normal — existing behavior, cross-platform; frontend presentation only.

## Product Contract

Trang `/chat` là không gian trao đổi nghiên cứu bằng tiếng Việt: lịch sử có tìm kiếm,
hội thoại dễ đọc, phạm vi rõ ràng, ô nhập nằm trong màn hình và lỗi có hướng xử lý.
Giữ nguyên API, quyền, nội dung lịch sử, nguồn gốc ChatGPT và duyệt đề xuất tri thức.

## Relevant Product Docs

- `Docs/Research System Implementation Plan.md`
- `Docs/Quy uoc ngon ngu tieng Viet.md`
- `docs/stories/research-workspace-ui-redesign.md`

## Acceptance Criteria

- Desktop có lịch sử riêng; mobile thu gọn lịch sử để ưu tiên hội thoại.
- Tìm kiếm tiêu đề, trạng thái chọn và tải/lỗi/rỗng rõ ràng.
- Tạo mới/nhập ChatGPT có biểu mẫu rộng, hủy được; gợi ý chỉ chuẩn bị câu hỏi.
- Enter gửi, Shift+Enter xuống dòng, bảo vệ quá trình nhập bộ gõ tiếng Việt.
- Lỗi lịch sử có giải thích tiếng Việt và mã lỗi trong phần chi tiết.
- Markdown, ảnh, chọn đoạn để hỏi AI và liên kết duyệt đề xuất tiếp tục hoạt động.

## Design Notes

Nền trắng ấm, xanh teal làm điểm nhấn, header nhỏ; giới hạn chiều rộng bài trả lời,
ô nhập cố định trong cột hội thoại, lịch sử cuộn độc lập. Không thay đổi nhà cung cấp AI.

## Validation

- Unit: bộ test chat, Markdown, app shell; tìm kiếm và lỗi lịch sử.
- Integration: ESLint, TypeScript, production build.
- E2E: tạo/gửi, nhập ChatGPT, bố cục desktop/tablet/mobile.
- Platform: kiểm tra trực quan và frontend Docker ở cổng 13000.

## Harness Delta

Intake #7. Không thay đổi quy tắc Harness.

## Evidence

- ESLint và TypeScript đạt; 11/11 kiểm thử chat, Markdown và app shell đạt.
- Next.js production build đạt trên 15 route trong container frontend.
- Playwright tạo/gửi bằng Enter, Shift+Enter, bảo vệ IME, gợi ý, tìm kiếm không dấu,
  lỗi lịch sử và nhập ChatGPT đạt trên desktop/tablet/mobile (9/9).
- Đã kiểm tra ảnh chào mừng, hội thoại và lỗi. Sửa cuộn cuối không phù hợp khi hội thoại
  mới chưa có tin nhắn để tiêu đề chào mừng trên mobile luôn xuất hiện từ đầu.
- Frontend chạy tại `13000`; nút gửi nằm trong viewport; không cuộn ngang/lỗi JavaScript.
- Chỉ restart frontend với source bind mount; lệnh khởi động build lại production.
  Không rebuild image hay chạm API, worker, database hoặc Smart Exam.
