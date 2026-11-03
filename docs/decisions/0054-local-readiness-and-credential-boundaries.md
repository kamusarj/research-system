# 0054 Hoàn thiện local và ranh giới credential CLI

Date: 2026-11-03

## Status

Accepted — người dùng yêu cầu làm hết việc tiếp theo, tự tạo owner và chưa có tên miền.

## Decision

Giữ kiến trúc local-first và quyền phê duyệt của con người. Tắt công cụ thực thi của Codex;
Antigravity chỉ thấy Secret Service broker với đúng credential ứng dụng của nó. Cài mã bridge
ra ngoài repo. Tạo mật khẩu owner ngẫu nhiên trong tệp riêng trên máy và bật local auth sau
kiểm chứng. Lên lịch backup cục bộ; offsite/HTTPS và gói ChatGPT thật cần đầu vào bên ngoài.
Tối ưu chat/research phải giữ hợp đồng dữ liệu, verifier và điều kiện nguồn.

## Consequences

Không đọc được các keyring item khác qua sandbox. Refresh vẫn cập nhật đúng credential đã được
allowlist, không sao chép cả keyring. Bridge cần Python hệ thống với dbus/gi và dbus-daemon;
thiếu chúng phải báo unavailable, không trở về proxy toàn keyring.

## Evidence / Sources

- `docs/stories/remaining-local-readiness/validation.md`.
- [OpenAI Codex configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agent-file-schema)
  xác nhận có thể tắt `features.shell_tool`; CLI đang cài xác nhận flag này là stable.
