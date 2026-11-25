# Exec Plan

## Goal

Sửa đủ12 phát hiện audit đã được chủ sở hữu yêu cầu ngày2026-11-20; kiểm chứng bằng regression.

## Scope and Risk

High-risk, intake21: quyền xuất bản, giữ bằng chứng canonical, restore, concurrency/lease, verifier,
cache/CPU, báo cáo, tìm kiếm, secret worker và bộ giới hạn tần suất.
Giữ mọi thay đổi trước đó và nguyên tắc human review. Không đổi provider hoặc chạy benchmark tốn quota.

## Phases

1. Đọc trạng thái hiện tại; bootstrap/intake/decision/story.
2. Sửa P1 quyền tài liệu/bằng chứng/restore; song song sửa research và search/runtime.
3. Regression và toàn bộ kiểm tra phù hợp; migration PostgreSQL tách biệt nếu cần lease token mới.
4. Refresh runtime cục bộ sau khi checks đạt; cập nhật proof và bàn giao.

## Stop Conditions

Hỏi lại chỉ khi cần thay kiến trúc, xóa dữ liệu thực, đổi chính sách quyền đã chấp nhận hoặc hạ
chuẩn kiểm chứng. Migration lease nếu cần chỉ additive, không xóa/backfill phá dữ liệu.
Không diễn tập restore ghi đè DB thật; không tải model/prune tài nguyên dự án khác.
