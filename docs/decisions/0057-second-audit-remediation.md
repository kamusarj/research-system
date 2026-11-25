# 0057 Follow-up audit: publication, provenance and bounded execution

Date: 2026-11-20

## Status

Accepted — user yêu cầu bắt đầu sửa12 phát hiện đã xác nhận.

## Decision

Thực thi nhất quán owner-only publish và giữ canonical evidence theo0042/0048 tại service boundary.
Fencing ngăn worker đã mất lease ghi vào run; nếu cần thêm token thì migration chỉ additive.
Verifier từ chối duplicate/conflicting output, TTL24h áp dụng mọi cache entailment; matcher có
ngân sách tính toán, report không đánh đồng omission với absence. Search giữ filter, task secret
được cấp nhất quán và limiter thu hồi bucket hết hạn. Restore phải dừng ngay khi lỗi trước resume.

## Consequences

Giữ human review, provider mặc định, benchmark quality gates và artifact lịch sử. Không restore
ghi đè hoặc xóa dữ liệu thật để kiểm thử. Dùng regression và PostgreSQL tách biệt cho concurrency.

## Follow-Up

`docs/stories/second-audit-remediation/validation.md`; KPI20% và local model/SSH thật vẫn là proof riêng.
