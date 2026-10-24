# 0047 Kiểm tra mô hình trước khi kết nối API cá nhân

Date: 2026-09-05

## Status

Accepted — phản hồi trực tiếp của chủ dự án; mở rộng DEC-059/0046 về validation.

## Context

Text model và lỗi provider chung khiến người dùng không biết sai key, thiếu tiền
hay không được dùng model. Model list không xác nhận được khả năng inference.

## Decision

Tải models động bằng key vừa nhập; kiểm tra adapter/model thực tế trước khi UI lưu
kết nối. Chỉ probe khi người dùng bấm nút đã ghi khả năng có phí; không tự probe
khi nhập key, tải danh mục hay tạo session. Tối đa 16 output token, timeout 20 giây,
không retry/fallback/tool execution. Trả mã lỗi riêng, không echo upstream text.
Không thay ephemeral storage và no-secret-log contract. Thành công không đảm bảo
credit/quyền tồn tại mãi; chat thực tế dùng cùng error classifier.

## Alternatives Considered

Danh mục cố định dễ lỗi thời. Kiểm tra chỉ bằng GET models không phát hiện hết
credit/model incompatibility. API số dư không thống nhất và không cần cho phạm vi này.

## Consequences

Một lần kiểm tra có thể bị nhà cung cấp tính phí; UI nói rõ trước khi bấm. Danh mục
có thể chứa model không phù hợp chat; probe từ chối với thông báo thay vì giả định.
Không biết số dư chính xác; quota chung không được diễn giải chắc chắn là hết tiền.

## Sources

- [OpenAI error codes](https://developers.openai.com/api/docs/guides/error-codes)
- [OpenAI list models](https://developers.openai.com/api/reference/resources/models/methods/list)
- [DeepSeek models](https://api-docs.deepseek.com/api/list-models/)
- [DeepSeek errors](https://api-docs.deepseek.com/quick_start/error_codes/)

## Follow-Up

Chỉ thêm provider mới hoặc lưu khóa nếu có yêu cầu riêng.
