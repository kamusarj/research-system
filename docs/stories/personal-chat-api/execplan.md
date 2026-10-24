# Exec Plan

Status: implemented; acceptance evidence in `validation.md`.

## Goal

Cho phép người dùng sử dụng API key riêng trong trang chat và chạy bản mới cục bộ.

## Scope

OpenAI/DeepSeek hiện có; key tạm thời, create/import/send và metadata nguồn khóa.

## Risk Classification

High-risk: authorization, audit/security, provider behavior, data model, public contract.
User yêu cầu bổ sung API cá nhân; mặc định khóa tạm được thông báo trong phiên.

## Work Phases

1. Đọc auth, provider, request validation, chat và migration hiện hành.
2. Ghi quyết định và triển khai request-scoped credentials với schema validation.
3. Tạo UI nhập khóa bằng password và phân biệt personal/system.
4. Kiểm tra không lộ/persist/chia sẻ khóa, không fallback, auth/CSRF, migration và browser.
5. Apply migration additive, restart API/frontend có scope và kiểm tra runtime.
6. Cập nhật log và detailed trace.

## Stop Conditions

Nếu cần endpoint tùy ý hoặc lưu khóa lâu dài, thiết kế lại ranh giới theo lựa chọn
người dùng trước khi thêm; không tự chuyển credential sang persistent storage.
