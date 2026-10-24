# 0051 Pipeline nghiên cứu sâu có trích dẫn và gia cố bảo mật cục bộ

Date: 2026-10-24

## Status

Accepted

## Context

Chủ sở hữu yêu cầu tối ưu toàn diện chất lượng research, UI/UX và bảo mật với tiêu chí đo được
(100% nhận định trong báo cáo có nguồn kèm link, giảm thời gian/token, Lighthouse ≥ 90, không còn lỗ
hổng Critical/High). Audit 2026-10-24 cho thấy hệ thống chưa có luồng câu hỏi → báo cáo, không có
web search, không đo được token, cổng cục bộ mở LAN khi tắt đăng nhập và có phụ thuộc Critical/High.

## Decision

- Thêm pipeline nghiên cứu sâu planner → searcher → verifier → writer trong worker (từng bước có
  lease/checkpoint), nguồn web từ SearXNG tự host (profile `research-agent`, không mở cổng) và kho
  nghiên cứu đã duyệt. Nhận định chỉ được dùng khi trích dẫn nguyên văn khớp nguồn và qua kiểm tra
  suy luận; writer chỉ trả câu + mã nhận định, máy chủ gắn trích dẫn và từ chối báo cáo có câu không
  nguồn. Kết quả luôn là bản nháp `deep-research-report` cần chủ sở hữu duyệt (giữ quyết định khóa).
- Prompt dùng chỉ dẫn hệ thống chung; nội dung không tin cậy chỉ nằm trong `<source>` đã làm sạch.
- Ghi độ trễ/token mỗi lời gọi AI vào `ai_call_metrics` (không lưu nội dung).
- Cổng cục bộ chỉ nghe `127.0.0.1`; `RequestGuardMiddleware` chặn Host lạ và request đổi dữ liệu
  cross-site; chế độ nhóm chỉ tin `X-Forwarded-For` từ mạng Docker (thay `*` của DEC-061).
- Giới hạn tần suất mọi route tiêu tốn quota AI; ghim IP khi tải nguồn; CSP cho giao diện; che chuỗi
  giống khóa trong đầu ra AI; tài khoản dịch vụ có thêm scope `research:run`/`research:read`.
- Giao diện có design token, chế độ tối, viền focus rõ; khung ứng dụng vẽ ngay khi đang kiểm tra phiên.

## Alternatives Considered

1. API tìm kiếm trả phí (Brave/Tavily): chất lượng ổn định hơn nhưng tốn phí; để sau qua `SearchProvider`.
2. Chỉ dùng kho nội bộ: an toàn nhất nhưng độ phủ quá thấp (lượt chạy thử chỉ 1 nguồn, 1 góc nhìn).
3. Để writer viết Markdown tự do rồi kiểm tra trích dẫn: không đảm bảo được 100% câu có nguồn.
4. CSP dùng nonce: buộc mọi trang render động; chọn `'unsafe-inline'` cho script, chặn tải ngoài.

## Consequences

Positive:

- Báo cáo có trích dẫn kiểm chứng được tới câu gốc; số đo chi phí theo lượt và theo tác vụ.
- Không còn lỗ hổng phụ thuộc Critical/High; LAN không còn truy cập được khi tắt đăng nhập.

Tradeoffs:

- Chất lượng nguồn web phụ thuộc engine của SearXNG (Brave/DuckDuckGo có thể chặn IP máy chủ).
- Bảo đảm "100% câu có trích dẫn" là cấu trúc + từ vựng; độ tin cậy của nguồn vẫn do người duyệt.
- Ảnh SearXNG chiếm thêm đĩa; `/` của máy cục bộ còn ít dung lượng.

## Follow-Up

- Bật `AUTH_MODE=local` cục bộ sau khi chủ sở hữu tạo tài khoản (`make local-owner`).
- Container API/worker chạy non-root và mount mã chỉ đọc; thu hẹp sandbox CLI (keyring, `auth.json`).
- Điều hướng mobile dạng thanh dưới; tối ưu `/chat` trên mobile (Lighthouse 80).
