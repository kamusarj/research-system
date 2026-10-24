# 0046 API cá nhân tạm thời cho trò chuyện

Date: 2026-09-05

## Status

Accepted — user yêu cầu API cá nhân; mặc định giữ tạm trong trang đã được thông báo.

## Context

Khóa máy chủ không đáp ứng nhu cầu từng người dùng tự cung cấp API cho chat.

## Decision

Cho phép researcher/owner nhập khóa của họ và mô hình cho OpenAI/DeepSeek hiện có.
Khóa chỉ ở bộ nhớ trang và request server; không lưu browser storage/database/log.
Lưu `credential_source` không nhạy cảm để personal sessions luôn cần key người gọi,
không fallback sang system key. Dùng endpoint HTTPS cố định và provider instance riêng.
Chat vẫn shared theo hợp đồng nhóm hiện có; không dùng key của người khác.

Quyết định này mở rộng DEC-010/018/019: chỉ khóa do chính người dùng nhập có mặt tạm
trong browser; khóa cấu hình máy chủ tiếp tục không bao giờ được trả về browser.

## Alternatives Considered

Vault mã hóa theo tài khoản cần chính sách lưu/rotation/master key riêng; plaintext
browser/database storage không được dùng.

## Consequences

Người dùng phải nhập lại khi tải lại/rời trang hoặc đăng xuất. Không có API lấy lại
khóa, không tự kiểm tra kết nối có phí. API cá nhân chỉ áp dụng graph chat.

Cập nhật cùng ngày theo yêu cầu người dùng: `0047-personal-chat-model-validation.md`
thêm tải danh mục model và probe có giới hạn khi người dùng chủ động bấm kiểm tra
sau thông báo khả năng có phí. Không tự probe khi nhập khóa hay tải danh mục; các
quy tắc giữ khóa tạm ở quyết định này vẫn giữ nguyên.

## Follow-Up

Chỉ thêm lưu theo tài khoản hoặc endpoint khác khi người dùng chọn phạm vi đó.
