# Exec Plan

1. Rà soát song song ba mảng (pipeline/worker, đồ thị/chat/search/auth, frontend) ở chế độ chỉ đọc.
2. Hạ tầng: anchor môi trường chung API/worker, `init: true`, Dockerfile frontend nhiều stage,
   `docker-compose.team.yml`, `.env.team.example`, `scripts/team.sh`, Makefile, autostart nhận chế độ nhóm.
3. Backend: phân quyền duyệt, máy trạng thái change set, duyệt link nguyên tử, lease tối đa, hạn
   tổng tải nguồn, RSS qua bộ tải an toàn, inline chỉ PDF + CSP, giải phóng kết nối khi gọi AI,
   giới hạn tần suất theo người dùng + khóa đăng nhập sai theo tài khoản, đổi mật khẩu tự phục vụ.
4. Frontend: hết phiên → màn đăng nhập, xác nhận cookie sau đăng nhập, phân trang, xử lý lỗi thao
   tác, trang Thành viên/Tài khoản, security headers.
5. Kiểm chứng: toàn bộ test, stack nhóm cô lập (`bai-teamcheck`) gồm HTTPS Caddy, sao lưu/khôi phục,
   dừng worker; cập nhật runtime cục bộ sau khi sao lưu.
