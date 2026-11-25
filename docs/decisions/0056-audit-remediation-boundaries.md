# 0056 Audit remediation boundaries

Date: 2026-11-19

## Status

Accepted — chủ sở hữu yêu cầu thực hiện toàn bộ đề xuất audit và thử Mistral.

## Decision

Giữ nguyên kiến trúc/provider mặc định và human review. Tăng ràng buộc giữa báo cáo và verified
claims, fail closed với credential/deadline, tái sử dụng backup nhất quán, áp dụng lockfile khi
khởi động và mở rộng proof CI. Số đo evaluation phải bao gồm thất bại và nguồn gốc cấu hình.
Probe Mistral dùng dữ liệu tổng hợp, ngân sách nhỏ; không ghi credential hay dữ liệu thật vào log.

## Consequences

Không nâng major framework hoặc tự tải local model. Không đổi baseline để tuyên bố đạt KPI.
Những kiểm chứng cần model/SSH/domain thật vẫn phải ghi là chưa đạt nếu không có tài nguyên.

## Follow-Up

Evidence: `docs/stories/audit-remediation/validation.md`.
