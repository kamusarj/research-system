# 0052 Mỗi người dùng tự kết nối gói ChatGPT của mình (Sign in with ChatGPT)

Date: 2026-10-27

## Status

Accepted

## Context

Chủ sở hữu muốn khi đưa hệ thống lên web, mỗi người dùng tự kết nối tài khoản của họ để việc AI
dùng quota riêng thay cho khóa/quota của chủ máy. DEC-062 cấm dùng chung gói CLI cá nhân của chủ máy
cho cả nhóm. Từ 29/09/2026 OpenAI có "Sign in with ChatGPT" + ChatGPT plan usage: người dùng Plus/Pro
cho phép một ứng dụng gọi Responses API bằng access token OAuth của chính họ, tính vào hạn mức gói
(có giới hạn riêng cho từng ứng dụng trong cài đặt ChatGPT). Luồng tự đăng ký
(`dynamic_agent_client`) dành cho ứng dụng mã nguồn mở/chạy trên máy người dùng và bắt buộc callback
loopback `127.0.0.1`; ứng dụng chạy trên web hoặc thu phí phải điền form đối tác và chờ OpenAI cấp
client ID.

## Decision

- Thêm nhà cung cấp `chatgpt_plan`: OAuth Authorization Code + PKCE + OIDC tới `auth.openai.com`
  (scope `offline_access resource.invoke chatgpt.tokens.use.direct`, `resource=https://api.openai.com/v1`),
  kiểm chữ ký/issuer/audience/nonce của ID token, kiểm scope gói trước khi suy luận.
- Hai chế độ cùng một mã: không có `CHATGPT_PLAN_CLIENT_ID` = cục bộ (tự đăng ký, callback
  `127.0.0.1` rồi chuyển tiếp sang trang web để hoàn tất trong phiên đăng nhập); có client ID do OpenAI
  cấp = bản web (callback HTTPS đã đăng ký, có thể là client bảo mật với secret). Môi trường
  staging/production từ chối khởi động nếu bật mà thiếu client ID.
- Token chỉ lưu mã hóa Fernet (`CREDENTIALS_ENCRYPTION_KEY`, hỗ trợ xoay khóa); không vào log, URL,
  trình duyệt hay nhật ký kiểm toán. Làm mới token tuần tự hóa bằng khóa hàng vì refresh token xoay
  vòng; đăng xuất thu hồi refresh token tại OpenAI.
- `state` dùng một lần, hết hạn 10 phút và chỉ hoàn tất được trong phiên của người đã bắt đầu (chặn
  việc lừa người khác gắn gói của họ vào tài khoản kẻ tấn công).
- Ai trả quota: việc nền tính vào người tạo việc (link: người gửi; tài liệu: người tải lên — cột mới
  `requested_by`; nghiên cứu sâu: người tạo lượt); việc trong request (chat, sửa tài liệu) tính vào
  người đang thao tác. Việc dùng gói của người khác chỉ người tạo mới chạy lại được.
- Không tự chuyển sang khóa API của máy chủ khi gói hết hạn mức (yêu cầu của OpenAI); báo lỗi rõ
  kèm liên kết "Quản lý mức dùng". Tài khoản dịch vụ (Discord…) luôn dùng cấu hình máy chủ.
- Gọi Responses với `store=false`, `stream=true`, không gửi temperature/max_output_tokens; JSON
  schema không strict rồi kiểm lại bằng Pydantic. Chat có công cụ dùng giao thức JSON của nhà cung cấp
  CLI. Embedding vẫn dùng API của máy chủ (plan usage chỉ hỗ trợ Responses).

## Alternatives Considered

1. Người dùng tải `~/.codex/auth.json` lên máy chủ: không phải cách OpenAI cho phép với ứng dụng
   chạy trên web, máy chủ giữ token toàn quyền của nhiều người, Codex còn chạy lệnh trên máy chủ.
2. Trình kết nối chạy trên máy người dùng: token không rời máy họ nhưng phải cài đặt và máy phải bật.
3. Người dùng tự nhập API key OpenAI: đơn giản nhưng tính tiền theo token, không dùng quota gói.

## Consequences

Positive:

- Người dùng tự trả quota AI bằng gói của họ; máy chủ không cần khóa API cho các việc đó.
- Chạy được ngay ở chế độ cục bộ để chủ máy kiểm chứng; bản web chỉ cần thêm client ID khi được duyệt.

Tradeoffs:

- Bản web phụ thuộc việc OpenAI duyệt form đối tác; hợp đồng cho đối tác chưa công khai đầy đủ nên các
  tham số khác chế độ cục bộ để cấu hình được (secret, callback).
- Preview của OpenAI có thể đổi (tham số không hỗ trợ, mã lỗi); lỗi được ánh xạ theo tài liệu 10/2026.
- Gói Plus có giới hạn 5 giờ dùng chung với mọi ứng dụng; nghiên cứu sâu tốn nhiều lượt.

## Follow-Up

- Linh điền form https://openai.com/form/sign-in-with-chatgpt-interest/ cho bản web.
- Kiểm chứng end-to-end bằng tài khoản thật ở chế độ cục bộ.
- Nếu muốn máy chủ không bao giờ trả tiền AI cho người dùng: thêm chế độ bắt buộc gói riêng (chặn cả
  lựa chọn nhà cung cấp của máy chủ cho việc do người dùng khởi chạy).
