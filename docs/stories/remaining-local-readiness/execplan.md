# Exec Plan

## Goal / Risk

Hoàn tất backlog Now có thể làm trên máy, không dừng sau một mục. Intake #16,
US-REMAINING-LOCAL-READINESS, high-risk: security/auth/provider/operations/existing behavior.
User đã yêu cầu tự tạo owner; chưa có tên miền nên giữ bản local và chuẩn bị bản team.

## Work Phases

1. CLI: tool policy, keyring broker, install ngoài repo, unit + sandbox canary + provider probe.
2. Vận hành: backup trước đổi cấu hình, owner, auth, backup timer, hooks, provider readiness.
3. Hiệu năng: chat Lighthouse/bundle, research context và deterministic/token regression proof.
4. Kiểm tra hệ thống, cập nhật docs/logs/Harness, phân biệt việc đã xong với đầu vào bên ngoài.

## Stop Conditions

Không xóa dữ liệu/tài nguyên project khác. Không bỏ verifier/hạ validation để đạt token target.
Không đăng nhập/đồng ý thay người dùng tại nhà cung cấp; không tạo key/domain giả.

## Progress

- Discovery xong: owner chưa tồn tại, Gemini key thiếu, chưa có tên miền. Bắt đầu CLI.
