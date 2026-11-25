# Overview

## Current Behavior

Audit tái hiện12 lỗi: sửa tài liệu approved qua version; xóa evidence canonical từ chat;
restore tiếp tục sau lỗi; quan hệ được xuất bản bởi researcher; stale worker ghi đè completed run;
verdict trùng/mâu thuẫn được chấp nhận; batch cache vượt TTL; report báo thiếu evidence giả;
fuzzy matcher quá tốn CPU; hybrid bỏ filter; worker thiếu provider secrets; limiter giữ bucket hết hạn.

## Target Behavior

Mỗi lỗi có regression kiểm chứng hành vi an toàn. Owner gate nằm tại service trước side effect;
tài liệu có evidence đã áp dụng được giữ lại; restore chỉ resume sau thành công; lease có fencing;
verifier fail closed và cache TTL nhất quán; báo cáo phân biệt thiếu bằng chứng/thiếu trình bày;
CPU có giới hạn; kết quả search tuân theo filter; API/worker nhận cùng secret tác vụ; limiter có cleanup.

## Affected Docs and Users

Owner/researcher/viewer và operator. Các hợp đồng hiện hành ở README, `Docs/Research System
Implementation Plan.md`, `Docs/Team Deployment Runbook.md`, decisions0042/0048/0054/0056.

## Non-Goals

Không tự duyệt/apply, không đổi provider/model/tier, không tuyên bố KPI20% bằng test tổng hợp.
