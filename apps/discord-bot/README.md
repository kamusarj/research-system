# Cổng tiếp nhận Discord

Đây là bộ điều hợp mỏng, chuyển liên kết công khai và tệp PDF từ các kênh Discord được cho phép sang API tiếp nhận của Hệ thống nghiên cứu. Bot không chứa logic nghiên cứu: việc trích xuất, phân loại, loại trùng và tạo đồ thị tri thức đều nằm trong API và worker (quyết định DEC-028). Vì vậy, có thể thay Discord bằng nền tảng trò chuyện khác mà không phải sửa các phần còn lại.

## Bot làm được gì

- Tự gửi mọi liên kết công khai hoặc PDF được hỗ trợ trong kênh cho phép. Người dùng không cần gọi `/submit`; lệnh này chỉ là cách nhập thủ công tùy chọn.
- Chỉ theo dõi máy chủ và kênh có trong danh sách cho phép. Danh sách rỗng có nghĩa là không theo dõi ở đâu; tiến trình sẽ từ chối khởi động thay vì mở quyền mặc định.
- Thu thập mọi liên kết công khai trong một tin nhắn và tệp PDF đính kèm tối đa 20 MB. Mỗi tin nhắn giới hạn 20 liên kết và 5 tệp; phần vượt giới hạn luôn được báo rõ.
- Tạo một biên nhận cho mỗi tin nhắn, định danh bằng ID tin nhắn Discord. Gửi lại cùng tin nhắn không tạo tác vụ trùng nhưng lần xuất hiện lặp lại vẫn được ghi nhận.
- Mặc định yêu cầu API tự duyệt URL theo điều kiện an toàn. Chỉ nguồn đầy đủ và đạt ngưỡng tin cậy mới được duyệt; nguồn thiếu nội dung hoặc có độ tin cậy thấp vẫn chờ con người kiểm tra.
- Tải và lưu dữ liệu tệp đính kèm qua API trước khi xử lý bất đồng bộ, tránh mất tác vụ khi URL CDN của Discord hết hạn.
- Dùng biểu tượng trạng thái và trả kết quả tiếng Việt cho từng mục: ⏳ đang xử lý, ✅ đã xuất bản, 📥 chờ duyệt, ⚠️ một phần, ♻️ đã thu thập, ❌ thất bại, 🚫 bị giới hạn.
- Giải thích lỗi người dùng có thể xử lý như tường phí, lớp chống bot, yêu cầu đăng nhập hoặc PDF quét; lỗi khác vẫn kèm mã để tra cứu mà không suy đoán nguyên nhân.
- Báo khoảng trống tri thức còn hoạt động và liên quan đến mục vừa duyệt. Việc phát hiện, lưu trữ và lọc khoảng trống vẫn do API đảm nhiệm.

## Lệnh gạch chéo

| Lệnh | Công dụng |
| --- | --- |
| `/help` | Xem toàn bộ lệnh, cách tự nhận liên kết và biểu tượng kết quả |
| `/guide` | Xem quy trình tiếp nhận nguồn, kiểm duyệt, đồ thị và khoảng trống tri thức |
| `/sources` | Xem loại nguồn, giới hạn truy cập và giới hạn dung lượng |
| `/ping` | Kiểm tra cổng Discord có phản hồi và xem độ trễ |
| `/pin message_id:<id>` | Ghim tin nhắn trong cùng kênh khi người gọi và bot đều có quyền |
| `/submit url:<link>` | Nhập thủ công một liên kết công khai |
| `/status message_id:<id>` | Xem kết quả của một tin nhắn đã gửi trước đó |

Phản hồi hướng dẫn, `/status` và `/pin` chỉ người gọi nhìn thấy. Mọi lệnh dùng cùng danh sách máy chủ/kênh cho phép với cơ chế tự tiếp nhận. Trạng thái của bot hướng người dùng mới tới `/help`; nếu nhắc tên bot mà không kèm nguồn phù hợp, bot cũng trả gợi ý này. Khi khởi động, các lệnh được sao chép và đồng bộ vào từng máy chủ được phép để có thể kiểm tra ngay.

`/pin` không tìm kiếm ở kênh khác và chỉ trả kết quả riêng tư. Cả người gọi lẫn bot đều cần quyền `PIN_MESSAGES`. Tin nhắn đã ghim được coi là thành công mà không lặp thao tác. Discord quản lý trạng thái ghim và nhật ký kiểm toán; API nghiên cứu và tài khoản dịch vụ không nhận thêm quyền.

## Phân quyền

Bot xác thực bằng tài khoản dịch vụ có phạm vi hẹp, không dùng phiên người dùng. Chủ sở hữu có thể tạo tài khoản trong giao diện web hoặc qua API:

```bash
curl -X POST http://localhost:18000/api/v1/auth/service-accounts \
  -H 'content-type: application/json' \
  -d '{"name":"Cổng Discord","source_namespace":"discord",
       "scopes":["intake:submit","intake:read-own"]}'
```

Token chỉ được trả về một lần. Hai phạm vi trên là toàn bộ quyền API của bot: bot không thể duyệt nguồn, xuất bản nghiên cứu hay thay đổi đồ thị tri thức.

## Cấu hình

Hệ thống đọc bí mật từ `/run/secrets/<tên viết thường>` nếu tệp tồn tại; nếu không thì đọc từ biến môi trường. Trong môi trường thật nên dùng tệp bí mật đã gắn vì giá trị không xuất hiện trong `docker inspect` hoặc danh sách tiến trình.

| Biến | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | có | Token bot của ứng dụng Discord |
| `RESEARCH_API_TOKEN` | có | Token tài khoản dịch vụ có phạm vi hẹp |
| `DISCORD_ALLOWED_GUILD_IDS` | có | Danh sách ID máy chủ, ngăn cách bằng dấu phẩy |
| `DISCORD_ALLOWED_CHANNEL_IDS` | có | Danh sách ID kênh, ngăn cách bằng dấu phẩy |
| `RESEARCH_API_URL` | không | Mặc định `http://api:8000` |
| `DISCORD_INTAKE_NAMESPACE` | không | Không gian tên của biên nhận, mặc định `discord` |
| `DISCORD_INTAKE_PROVIDER` | không | Cố định một nhà cung cấp AI cho các nguồn này |
| `DISCORD_AUTO_APPROVE_LINKS` | không | Yêu cầu tự duyệt có kiểm soát cho URL đầy đủ, tin cậy cao; mặc định `true` |
| `DISCORD_LOCALE` | không | Biến cũ được giữ để tương thích; sản phẩm luôn dùng tiếng Việt |
| `DISCORD_USER_RATE_LIMIT` | không | Số tin nhắn nhận từ mỗi người trong một phút, mặc định 10 |
| `DISCORD_POLL_INTERVAL_SECONDS` | không | Khoảng nghỉ giữa hai lần kiểm tra trạng thái, mặc định 5 giây |
| `DISCORD_POLL_ATTEMPTS` | không | Số lần kiểm tra trạng thái, mặc định 36 (ba phút) |

Ứng dụng Discord cần bật đặc quyền **Message Content**. Trong mỗi kênh được cho phép, bot cần các quyền View Channel, Send Messages, Add Reactions, Read Message History, Use Application Commands và **Pin Messages**. Người dùng gọi `/pin` cũng cần **Pin Messages**. Không thay các quyền này bằng Administrator.

## Chạy bot

```bash
# Chạy từ thư mục gốc sau khi hệ thống chính đã hoạt động
docker compose --profile discord up -d discord-bot
docker compose logs -f discord-bot
```

## Kiểm thử

```bash
# Chạy từ thư mục gốc; dùng lại trình chạy kiểm thử của môi trường phát triển API
PYTHONPATH=apps/discord-bot apps/api/.venv/bin/python -m pytest apps/discord-bot/tests
scripts/verify_discord_bot_commands.sh
```

Các quyết định của cổng — danh sách cho phép, nhận diện liên kết/tệp, tạo biên nhận, ý định tự duyệt có kiểm soát, ánh xạ kết quả/khoảng trống, giới hạn tần suất và cấu hình — đều được kiểm thử mà không cần kết nối Discord hoặc mạng. Phần ghép nối Discord trong `app/bot.py` được giữ mỏng và dễ đọc. Kiểm tra nhanh cây lệnh dựng ảnh production, xác nhận đủ bảy lệnh trong máy chủ cho phép và chạy callback `/pin` qua các trường hợp từ chối theo danh sách, thiếu quyền người gọi, thiếu quyền bot, lặp an toàn và thành công mà không dùng thông tin xác thực thật.

Xem hướng dẫn thiết lập và nghiệm thu tiếng Việt đầy đủ — gồm ứng dụng Discord, tài khoản dịch vụ tối thiểu quyền, ca kiểm tra tin nhắn thật, bằng chứng đồ thị/khoảng trống, xử lý sự cố và dọn dẹp — tại [`Docs/Discord Bot Test Runbook.md`](../../Docs/Discord%20Bot%20Test%20Runbook.md).
