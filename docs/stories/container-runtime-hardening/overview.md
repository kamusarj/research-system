# Overview

## Current Behavior

API/worker chạy bằng root, bind-mount mã nguồn có quyền ghi. Volume tài liệu cũ thuộc root.
Đây là phần còn lại của DEC-064/decision 0051, được tiếp tục theo yêu cầu ngày 2026-11-03.

## Target Behavior

- Tiến trình API/worker chạy UID/GID 10001, bỏ toàn bộ Linux capabilities và không nâng quyền.
- Hệ tệp gốc và mã nguồn chỉ đọc; chỉ volume tài liệu và `/tmp` được ghi.
- Volume cũ/mới được chuẩn bị trước khi ứng dụng chạy; giữ nguyên nội dung và mode, không theo symlink.
- Upload/read/delete tài liệu, migration, LaTeX và OCR vẫn hoạt động.

## Affected Users

Người vận hành môi trường cục bộ/nhóm và mọi vai trò dùng tài liệu.

## Affected Product Docs

`Docs/Team Deployment Runbook.md`, `README.md`, decision 0053.

## Non-Goals

Không đổi đăng nhập, nhà cung cấp AI, schema, hạn mức hoặc quyền nghiệp vụ; không push/deploy web.
