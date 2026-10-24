# Exec Plan

Status: implemented; acceptance evidence in `validation.md`.

## Goal

Hoàn thiện chọn/kiểm tra API cá nhân theo phản hồi người dùng; cập nhật runtime.

## Scope

OpenAI/DeepSeek chat, discovery/verify, lỗi, responsive UI/tests/docs. Không migration.

## Risk Classification

High-risk: audit/security, external provider, public contract, existing behavior,
cross-platform. Hướng đã rõ qua yêu cầu trực tiếp; không cần quyết định lưu key mới.

## Work Phases

1. Đối chiếu official API docs và baseline.
2. Phân loại lỗi chung, discovery/verify endpoint, auth/rate/secret tests.
3. Select + verification UI, ngăn stale results và kiểm tra model phiên cũ.
4. Unit/integration/E2E/build; restart riêng API/frontend và smoke.
5. Cập nhật logs, proof, decision và detailed trace.

## Stop Conditions

Dừng nếu cần lưu khóa hoặc đổi provider/quyền/schema ngoài phạm vi.
