# Design

## Boundaries

- Codex: tắt shell/unified exec/subagent và các công cụ ngoài; vẫn bwrap, HOME tách biệt.
- Antigravity: Secret Service riêng, chỉ forward credential có service=gemini/username=antigravity;
  kiểm tra path/session/attributes cho cả đọc và refresh. Không forward keyring toàn tài khoản.
- Bridge: bản sao đã kiểm chứng ở thư mục ứng dụng riêng của user, mode 0500; systemd không chạy
  mã từ repo. Module DBus dùng gói Python hệ thống dbus/gi và dbus-daemon; không thêm API dependency.
- Tạo owner bằng password ngẫu nhiên qua stdin; thông tin đăng nhập chỉ trong tệp 0600 ngoài repo.
  Bật AUTH_MODE=local sau khi kiểm tra tài khoản; không ghi thông tin đó vào AI_LOGS.
- Backup local định kỳ vào thư mục riêng, quyền 0700/0600, kiểm tra archive; không xóa backup thủ
  công và không chọn dịch vụ ngoài máy thay chủ sở hữu.
- Hiệu năng: đo trước/sau; tải chậm các phần Markdown/API settings chưa dùng; giảm context lặp
  ở pipeline, giữ verifier và các điều kiện nguồn/trích dẫn.

## External Inputs

Form OpenAI, tài khoản ChatGPT thật, Gemini key, tên miền/đích offsite và nghiệm thu sản phẩm
vẫn cần người sở hữu. Các kiểm tra chỉ ghi trạng thái, không sao chép credential/PII vào log.
