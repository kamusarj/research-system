# Design

## Domain Model / Interface Contract / Data Model

Giữ hợp đồng hiện tại. Chỉ đổi danh tính hệ điều hành của tiến trình và quyền sở hữu tệp tài liệu.

## Application Flow

`document-storage-init` → API migration/start và worker. Bước init dùng cùng ảnh API, root với
chỉ `CHOWN`/`DAC_OVERRIDE`, không mạng, không biến môi trường/secret và chỉ mount volume tài liệu.
Descriptor thư mục và thao tác không theo symlink giới hạn việc sửa quyền trong volume. Không chmod
hay sửa byte nội dung; mục đúng UID/GID được bỏ qua. Lỗi init chặn ứng dụng khởi động.

## UI / Platform Impact

Ảnh mặc định USER 10001:10001. Compose local, multi-user và team dùng root filesystem chỉ đọc,
bỏ capabilities, `no-new-privileges`, `/tmp` tmpfs 512 MiB noexec/nosuid. Bind-mount `/app:ro` trong
chế độ local; team dùng mã trong ảnh. UID/GID cố định giữ quyền ổn định qua các lần build.

Mỗi API/worker có cgroup PID/thread limit 256; init có 64. LaTeX dùng giới hạn cgroup khi
`pids.max` được thực thi với giá trị 1–256, thay vì RLIMIT_NPROC tính theo toàn bộ host UID.
Ngoài cgroup hữu hạn này vẫn giữ `--nproc=32`. CPU, bộ nhớ, số file descriptor, cỡ tệp, timeout
và tắt shell escape giữ nguyên. Canary 40 luồng phụ tái hiện và ngăn lỗi khi chuyển sang non-root.

Dockerfile tách dependency/runtime; mặc định vẫn build dependency từ lockfile. Máy cục bộ dùng
ảnh root đã kiểm chứng với hash uv.lock trùng để tránh tải/cài lại lớp TeX/OCR khi thiếu đĩa.

## Observability

Init chỉ ghi số mục đổi quyền; không ghi tên tệp, nội dung hay thông tin xác thực.

## Alternatives Considered

1. Entry point giữ root: khiến ứng dụng dễ vô tình tiếp tục chạy root.
2. Chmod 777 volume: cấp quyền quá rộng và mất chế độ riêng tư của tài liệu.
3. Chown thủ công ở mỗi lần nâng cấp: dễ bỏ sót và làm hỏng autostart/khôi phục.
