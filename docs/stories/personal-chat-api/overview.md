# API cá nhân cho trò chuyện

## Current Behavior

Chat dùng khóa OpenAI/DeepSeek chung từ cấu hình máy chủ.

## Target Behavior

Người nghiên cứu có thể nhập API key và tên mô hình riêng, tạo hoặc nhập cuộc trò chuyện
với lựa chọn API cá nhân. Khóa chỉ ở bộ nhớ trang đang mở và bộ nhớ yêu cầu máy chủ;
không lưu vào database, browser storage, log hay nội dung chat. Tải lại/rời trang hoặc
đăng xuất cần nhập lại. Cuộc trò chuyện cá nhân thiếu khóa không dùng khóa hệ thống.

## Affected Users

Researcher/owner; viewer chỉ đọc theo quyền hiện có. Chat vẫn là kho hội thoại chung
của nhóm theo hợp đồng hiện tại; API key cá nhân không làm lịch sử trở thành riêng tư.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/decisions/0046-ephemeral-personal-chat-api.md`
- `README.md`

## Non-Goals

Lưu khóa lâu dài, endpoint tùy chỉnh, nhà cung cấp mới, thay đổi quyền đọc hội thoại,
API cá nhân cho worker/tài liệu/collector, kiểm thử AI có phí tự động.
