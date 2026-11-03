# Overview

## Current / Target Behavior

Người dùng yêu cầu hoàn tất các việc tiếp theo (2026-11-03), tự tạo tài khoản owner và xác nhận
chưa có tên miền. Tiếp tục toàn bộ việc kỹ thuật trong nhóm Now: cầu nối CLI, hiệu năng chat,
token research, xác thực cục bộ, backup tự động, kiểm tra provider và đồng bộ trạng thái.

## Affected Users / Docs

Chủ sở hữu cục bộ; `README.md`, runbook nhóm, AI_LOGS, decisions 0049/0051/0053/0054.

## Non-Goals / External Inputs

Không triển khai web nhóm khi chưa có tên miền; không tự cấp khóa Gemini/client ID OpenAI,
không ký thay nghiệm thu sản phẩm. Không mở rộng các tính năng Later chưa chọn (ontology,
Redis, collector mới). Các thay đổi phiên container trước được giữ nguyên.
