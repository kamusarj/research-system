# Overview

## Current Behavior

- Không có luồng câu hỏi → báo cáo; "nghiên cứu sâu" chỉ tạo template draft.
- Usage token bị bỏ; ngữ cảnh chat ~10.400 token vào/lượt; tài liệu gửi 2 lần cho 2 lời gọi.
- `next` 15.5.23 có advisory Critical; `pypdf`/`pillow` nhiều advisory; cổng 13000/18000 nghe
  `0.0.0.0` khi `AUTH_MODE=disabled`.
- UI chưa có dark mode/token ngữ nghĩa/primitive/skeleton; báo cáo hiển thị `<pre>`.

## Target Behavior

- Người dùng nhập câu hỏi, thấy tiến độ từng bước (lập kế hoạch/tìm kiếm/kiểm chứng/viết) và nhận
  báo cáo draft trong đó mọi claim có trích dẫn `[n]` bấm được tới nguồn đã xác minh.
- Chi phí và độ trễ AI đo được; token giảm ≥20% ở các luồng hiện có.
- Không còn lỗ hổng Critical/High; truy cập cục bộ chỉ từ máy chủ và phải đăng nhập.
- Giao diện nhất quán, có dark mode, Lighthouse ≥ 90.

## Affected Users

- Owner, researcher, viewer của nhóm.

## Affected Product Docs

- `README.md`, `Docs/Research System Architecture Design.md`, `Docs/Team Deployment Runbook.md`.

## Non-Goals

- Tự xuất bản báo cáo không qua người duyệt.
