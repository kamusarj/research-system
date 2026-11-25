# Dọn journal lưu trữ của hệ thống

## Yêu cầu

Linh yêu cầu dọn journal hệ thống đã lưu trữ theo mức khoảng 400 MiB. Harness intake 33, lane tiny.

## Quyết định và tệp thay đổi

Dùng thao tác vacuum một lần với xác thực hệ điều hành. Dọn file đã lưu trữ và giữ file đang ghi.
Cập nhật `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và log phiên này.

## Lệnh và kiểm chứng

- `journalctl --vacuum-size=400M` thu hồi 807,8 MiB từ 61 file đã lưu trữ.
- `journalctl --disk-usage` báo tổng 398 MiB. Theo block cấp phát, journal lưu trữ còn 366,1 MiB
  và journal đang ghi có 32 MiB trước và sau.
- `df -B1` báo dung lượng khả dụng tăng từ 8.896.782.336 B lên 9.743.831.040 B.
- `systemctl is-active systemd-journald` trả `active`. API health và `/graph` đều trả 200.
- `git diff --check` và kiểm Markdown đạt.

## Vấn đề còn lại và bước kế tiếp

Journal tiếp tục tích lũy theo cấu hình hệ thống. Phân vùng `/` còn 9,74 GB khả dụng.
