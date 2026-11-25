# Kiểm kê và dọn phân vùng root

## Yêu cầu

Linh yêu cầu đọc các thư mục không hiện trong Disk Usage Analyzer và dọn dung lượng. Harness intake 30, lane tiny.

## Quyết định và tệp thay đổi

- Đọc thống kê thư mục bằng quyền quản trị qua xác thực hệ điều hành. Dọn package cache và
  các revision Snap có cờ `disabled`. Giữ ứng dụng Snap đang chạy và dữ liệu của người dùng.
- Dọn thêm blob tải xuống Snap khớp dạng digest, đã cũ và có đúng một hard link trong cache.
  Kiểm tra không có Snap change đang chạy. Cơ chế cache được đối chiếu với
  [mã nguồn snapd](https://github.com/canonical/snapd/blob/master/store/cache.go).
- Dọn cache BuildKit và ba image công khai không container nào tham chiếu. Đã xác minh registry
  còn manifest theo digest cho `adminer:5.4.1`, `zricethezav/gitleaks:v8.30.1` và
  `cloudflare/cloudflared:2026.5.2` trước khi gỡ. ChromaDB là dependency của Smart Exam.
- Cập nhật `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và log phiên này.

## Lệnh và kiểm chứng

- `df -B1`, `du -x -s -B1`: `/var/lib/containerd` 17.566.527.488 B,
  `/var/lib/docker` 2.262.032.384 B, `/root` 84.975.616 B trước khi dọn. Hai thư mục container
  chiếm phần lớn dung lượng mà người dùng thường không đo được.
- `apt-get clean`, `snap remove <tên> --revision=<rev>` cho 10 bản vô hiệu hóa. Sau khi gỡ,
  các file Snap cũ vẫn còn trong cache tải xuống. Dọn 17 blob độc lập với tổng 3.813.048.320 B
  cấp phát. Xác nhận cache `.deb` trống, 27 Snap đang dùng và không còn bản `disabled`.
- `docker image rm` ba tag trên, `docker buildx prune --builder default --all --force`.
  Cache build còn 0 B. Danh mục container và volume trước/sau khớp. Kiểm hai image build
  ở intake 29 và hai image rollback còn tồn tại.
- Dung lượng khả dụng trên `/` từ 766.992.384 B lên 5.306.421.248 B, tăng 4,54 GB.
  API health và frontend `/graph` trả 200. `git diff --check` và kiểm Markdown đạt.

## Vấn đề còn lại và bước kế tiếp

`/` dùng 92% sau khi dọn. Các image đang dùng, container và volume dữ liệu vẫn có mặt.
Linh có thể tiếp tục nghiệm thu Weave/Graph v2 tại `:13000`.
