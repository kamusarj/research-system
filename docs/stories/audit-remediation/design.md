# Design

## Boundaries

Chặn đầu ra lỗi tại ranh giới provider; kiểm tra sau decode và giữ lỗi an toàn.
Writer chỉ có thể công bố nội dung được ràng buộc với claim đã xác minh; không hạ chuẩn verifier.
Tái sử dụng backup engine hiện có để tránh hai chính sách consistency/retention.
Không migration schema ứng dụng. Bộ test PostgreSQL dùng database tách biệt.

## Runtime and Evaluation

Khớp dependency volume với hash lockfile và cài đầy đủ trước build. CI dùng Node cùng runtime.
Usage attempt thất bại được cộng nếu provider đã báo usage; không ước lượng số token còn thiếu.
So sánh eval chỉ đủ điều kiện khi có cặp câu hỏi/config/chất lượng tương ứng và manifest tái lập.
Giữ baseline lịch sử để tránh thay đổi mục tiêu benchmark.

## Alternatives

Không dùng lexical overlap làm bằng chứng suy luận. Không dùng timeout từng read làm deadline tổng.
Không dùng npm force/major upgrade, pruning toàn Docker hoặc model giả thay nghiệm thu thật.
