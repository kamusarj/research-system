# 0053 Container ứng dụng không đặc quyền và volume tài liệu tương thích

Date: 2026-11-03

## Status

Accepted — triển khai phần follow-up của decision 0051 / DEC-064.

## Context

API/worker vẫn chạy root và ghi được mã nguồn; volume dữ liệu hiện có thuộc root. Chỉ đặt USER
sẽ làm hỏng upload hoặc tài liệu có mode riêng tư khi nâng cấp từ dữ liệu cũ.

## Decision

- USER cố định 10001:10001 trong ảnh, Compose API/worker bỏ capabilities, không nâng quyền,
  hệ tệp gốc/mã nguồn chỉ đọc; `/tmp` tmpfs và volume tài liệu là vùng ghi.
- One-shot `document-storage-init` root chỉ sửa UID/GID trong volume trước startup. Không mạng,
  không secrets, không source bind-mount; chỉ giữ CHOWN/DAC_OVERRIDE. Descriptor và nofollow giữ
  đích symlink ngoài volume không đổi. Không thay nội dung/mode của tệp.
- Local và team dùng cùng cơ chế; backup bảo toàn byte và restore bằng UID ứng dụng không khôi
  phục owner từ tar. Secret bind-mount phải cho GID 10001 đọc (0640), không mở quyền cho mọi người.
- Giới hạn 256 PID/thread mỗi container ứng dụng và 64 cho init. Khi cgroup `pids.max` ≤256,
  LaTeX dùng ranh giới này thay RLIMIT_NPROC theo host UID (đếm cả luồng/các container khác);
  môi trường không có ranh giới đó giữ `--nproc=32`. Các giới hạn LaTeX khác giữ nguyên.

## Alternatives Considered

1. Root entrypoint rồi hạ quyền; khó kiểm chứng USER và ranh giới root.
2. Chmod world-writable; không giữ quyền riêng tư của dữ liệu.
3. Khởi tạo thủ công; dễ bỏ sót khi nâng cấp/khôi phục.

## Consequences

Tác vụ bị chiếm quyền không sửa được mã/root filesystem hay nâng quyền. Volume cũ dùng được
sau init; tác vụ init tạm thời cần root và hai capabilities, giới hạn vào đúng volume.
Build ảnh mới cần hoàn tất trước `up --no-build`; tệp credentials 0600 root-owned cần điều chỉnh
nhóm đọc khi chủ sở hữu chọn cơ chế mounted secrets.

Thử nghiệm chuyển đổi phát hiện RLIMIT_NPROC=32 chặn xdvipdfmx vì các dịch vụ cùng UID đã có
72 luồng. Canary 40 luồng phụ và HTTP PDF thật chứng minh xử lý đúng trong ranh giới cgroup;
không bỏ giới hạn tài nguyên hoặc shell-escape guard.

## Follow-Up

Thu hẹp sandbox CLI và xác thực cục bộ tiếp tục theo TASKS; story này không đổi chúng.
