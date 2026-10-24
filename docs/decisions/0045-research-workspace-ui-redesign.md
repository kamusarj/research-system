# 0045 Thiết kế giao diện theo mô hình không gian làm việc nghiên cứu

Date: 2026-09-04

## Status

Accepted

## Context

Sản phẩm đã có đầy đủ các luồng nghiên cứu và đã chuyển sang tiếng Việt, nhưng giao diện cần một lần thiết kế lại tổng thể để giảm cảm giác của một bảng quản trị chung, cải thiện khả năng đọc lâu và giúp người dùng nhìn thấy tiến trình nghiên cứu rõ hơn trên mọi kích thước màn hình.

## Decision

Giữ nhận diện xanh đại dương hiện có nhưng tổ chức lại thành một “research workspace”: điều hướng xanh đậm có cấu trúc, nền nội dung dịu, typography giàu phân cấp, bề mặt phẳng với đường viền rõ, điểm nhấn teal dành cho hành động và trạng thái. Thay đổi được triển khai ở app shell, trang tổng quan và hệ thống token/component dùng chung, không đổi hợp đồng API hoặc quy tắc nghiệp vụ.

Các màn hình tiếp tục chỉ dùng tiếng Việt tự nhiên theo quyết định 0044. Responsive ưu tiên một sidebar đầy đủ trên desktop và điều hướng cuộn gọn trên màn hình hẹp. Hiệu ứng chuyển động phải tinh tế và tôn trọng `prefers-reduced-motion`.

## Alternatives Considered

1. Chỉ đổi màu và bo góc của giao diện hiện tại. Phương án này không giải quyết được phân cấp thông tin và cảm giác không gian làm việc.
2. Viết lại từng màn hình và luồng tương tác. Phương án này tăng rủi ro hồi quy nghiệp vụ trong khi mục tiêu của đợt thay đổi là trải nghiệm thị giác.

## Consequences

Positive:

- Mọi tuyến dùng chung một ngôn ngữ thị giác, dễ duy trì bằng token CSS.
- Mật độ thông tin và khả năng đọc phù hợp hơn với công việc nghiên cứu dài hạn.
- Rủi ro nghiệp vụ thấp vì giữ nguyên component logic và API.

Tradeoffs:

- CSS dùng chung phải tiếp tục hỗ trợ một số selector cũ để bảo toàn các màn hình phức tạp.
- Mọi thay đổi giao diện sau này cần kiểm tra cả layout sidebar desktop và navigation mobile.

## Follow-Up

- Dùng kiểm thử ảnh chụp đại diện khi thực hiện các thay đổi lớn tiếp theo về hệ thống thiết kế.
