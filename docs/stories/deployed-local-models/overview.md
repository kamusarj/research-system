# Overview

## Current Behavior

Ollama chỉ có generate cho tác vụ nền, không được chọn trong chat/document AI. Bản deploy chưa có
model inventory/picker/probe; bridge team còn kế thừa source mount cục bộ. Không có local OpenAI adapter.

## Target Behavior

Ollama và OpenAI-compatible local dùng được sau deploy, cùng máy hoặc máy cá nhân qua SSH/VPN.
Chat tải danh mục, kiểm tra model, pin model; worker dùng cấu hình operator. Endpoint/key chỉ ở server.

## Affected Users / Docs

Owner cấu hình triển khai; researcher chọn model; viewer đọc. Kế hoạch:
`Docs/Local Model Deployment Plan.md`; runbook nhóm và README.

## Non-Goals

Không tải model, mở model công khai, tự tạo tunnel credential hoặc thay provider mặc định/embedding.
Không nới tool/governance hoặc nhập URL tùy ý từ browser. Không đóng KPI token trong story này.
