# Sẵn sàng triển khai cho nhóm nghiên cứu

## Current Behavior

Chỉ chạy được ở chế độ cục bộ không đăng nhập (bind-mount mã, API mở cổng, frontend build lúc khởi
động). Worker thiếu nhiều biến cấu hình của API. Rà soát luồng phát hiện lỗ hổng phân quyền
(duyệt hàng loạt, ngưỡng tự duyệt RSS, tự duyệt từ nhà nghiên cứu, sửa nghiên cứu đã duyệt, đảo
trạng thái change set), XSS khi xem tệp HTML gốc, SSRF ở RSS, duyệt link không nguyên tử, worker
treo vì nguồn nhỏ giọt và nhận lại lease vô hạn, giới hạn tần suất dùng chung một IP proxy.

## Target Behavior

Một lớp phủ `docker-compose.team.yml` + `.env.team` + `scripts/team.sh`/`make team-*` dựng bản
production bắt buộc đăng nhập sau HTTPS (Caddy hoặc Cloudflare Tunnel), có sao lưu/khôi phục.
Chủ sở hữu quản lý thành viên ở `/members`, thành viên tự đổi mật khẩu ở `/account`. Các lỗi đã
xác nhận được sửa kèm kiểm thử hồi quy.

## Affected Users

Chủ sở hữu (vận hành, duyệt), nhà nghiên cứu (mất quyền tự xuất bản gián tiếp), người xem.

## Affected Product Docs

- `README.md`
- `Docs/Team Deployment Runbook.md`
- `docs/decisions/0048-team-deployment-and-review-gates.md`

## Non-Goals

SSO, Redis/rate limit đa máy, tiêu thụ `outbox_events`, đổi chuẩn hóa khóa tiếng Việt (cần migration
dữ liệu, chờ chủ sở hữu quyết định).
