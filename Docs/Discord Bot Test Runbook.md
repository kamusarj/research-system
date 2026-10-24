# Discord Bot Test Runbook

## 1. Mục tiêu

Tài liệu này giúp một tester cấu hình và nghiệm thu bot Discord theo luồng thật:

```text
Discord message
  -> Discord gateway
  -> intake receipt + worker
  -> research item
  -> relationship knowledge graph
  -> knowledge-gap detector
  -> phản hồi tại đúng kênh Discord
```

Runbook kiểm tra cả đường thành công, chờ duyệt, trùng lặp, nguồn chỉ lấy được một phần
và giới hạn allowlist. Bot không tự sửa hierarchy graph: placement vào hierarchy vẫn là
change set cần người duyệt.

Không đưa bot token, API token, provider key hoặc dữ liệu riêng tư vào tài liệu, Git,
ảnh chụp, issue hay `AI_LOGS/`.

## 2. Điều kiện trước khi test

- Docker Engine có Compose plugin.
- `curl`; nên có thêm `jq` để đọc JSON.
- Một Discord server dùng cho test và tài khoản có quyền cài application vào server.
- Một channel test mà bot được phép đọc và phản hồi.
- Một AI provider thật đã cấu hình; hệ thống không có mock provider trong runtime.
- Đã tạo Python environment của API nếu muốn chạy test tự động ngoài container.

Các cổng mặc định là API `8000` và web `3000`. Ví dụ bên dưới dùng `18000` và `13000`
để tránh xung đột với service khác trên máy.

## 3. Gate 1 — test tự động, chưa cần Discord token

Chạy từ repository root:

```bash
docker compose config -q
PYTHONPATH=apps/discord-bot \
  apps/api/.venv/bin/python -m pytest apps/discord-bot/tests
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_ingestion.py::test_discord_receipt_auto_approves_into_graph_and_reports_related_gap
scripts/verify_discord_bot_commands.sh
```

Kết quả đạt:

- Compose config hợp lệ.
- Toàn bộ test của Discord gateway pass.
- Backend proof xác nhận receipt có thể auto-approve vào graph và trả knowledge gap liên quan.
- Image `discord-bot` build thành công; command-tree smoke xác nhận đủ bảy lệnh được đăng ký
  và copy vào guild.

Nếu chưa có `apps/api/.venv`, làm theo phần local development trong `README.md`, rồi chạy
lại Gate 1.

## 4. Tạo Discord application

### 4.1 Tạo bot và lấy token

1. Mở [Discord Developer Portal](https://discord.com/developers/applications).
2. Chọn **New Application**, đặt tên riêng cho môi trường test.
3. Vào **Bot**; tạo/reset token rồi lưu token trong password manager.
4. Tại **Privileged Gateway Intents**, bật **Message Content Intent**.

Token là mật khẩu của bot. Nếu token từng xuất hiện trong chat, terminal recording, commit
hoặc ảnh chụp, reset token trước khi tiếp tục.

### 4.2 Cài bot vào server test

Trong phần **Installation**, cấu hình Guild Install với:

- Scopes: `bot`, `applications.commands`.
- Quyền tối thiểu tại channel test:
  - View Channel
  - Send Messages
  - Read Message History
  - Add Reactions
  - Use Application Commands
  - Pin Messages

Không cấp `Administrator`. Cài application vào server test, sau đó kiểm tra role của bot
không bị channel override từ chối các quyền trên.

Người dùng được phép chạy `/pin` cũng phải có **Pin Messages** trong channel test. Quyền
allowlist chỉ cho phép intake, không tự cấp quyền ghim.

### 4.3 Lấy ID cho allowlist

1. Bật **Developer Mode** trong Discord client.
2. Nhấp phải server và chọn **Copy Server ID**.
3. Nhấp phải channel test và chọn **Copy Channel ID**.

Chỉ ID có trong allowlist mới được bot xử lý. Allowlist rỗng làm bot từ chối khởi động.

## 5. Khởi động Research System

### 5.1 Tạo cấu hình local

Nếu repository chưa có `.env`:

```bash
test -f .env || cp .env.example .env
chmod 600 .env
git check-ignore .env
```

`git check-ignore` phải in ra `.env`. Sửa `.env` và chọn một provider thật, ví dụ:

```dotenv
API_PORT=18000
FRONTEND_PORT=13000
API_CORS_ORIGINS=http://localhost:13000
AUTH_MODE=disabled

AI_PROVIDER=mistral
MISTRAL_API_KEY=<provider-key-luu-cuc-bo>
DISCORD_INTAKE_PROVIDER=mistral
```

Có thể dùng provider khác đã được hệ thống hỗ trợ. `AUTH_MODE=disabled` chỉ phù hợp với
trusted local test; không dùng cấu hình này cho staging/production.

### 5.2 Chạy core stack và kiểm tra provider

```bash
docker compose up -d --build database api worker frontend
docker compose ps
curl -fsS http://localhost:18000/api/v1/health | jq
curl -fsS 'http://localhost:18000/api/v1/ai/providers?preflight=true' | jq
```

Kết quả đạt:

- `database`, `api`, `worker`, `frontend` đang chạy/healthy.
- Health trả `{"status":"ok"}`.
- Provider đã chọn có `configured: true` và preflight không báo lỗi kết nối/xác thực.

Preflight gọi provider thật và có thể phát sinh một network request nhỏ. Nó không trả về
credential hay nội dung provider response.

## 6. Tạo service account tối thiểu cho bot

Trong trusted local mode:

```bash
curl -fsS -X POST \
  http://localhost:18000/api/v1/auth/service-accounts \
  -H 'content-type: application/json' \
  --data '{
    "name": "Discord gateway local test",
    "source_namespace": "discord",
    "scopes": ["intake:submit", "intake:read-own"]
  }' | jq
```

Lưu riêng hai trường trong response:

- `id`: dùng để revoke sau test.
- `token`: chỉ được trả một lần; dùng làm `DISCORD_RESEARCH_API_TOKEN`.

Hai scope trên chỉ cho bot submit intake và đọc receipt trong namespace của chính nó. Bot
không có quyền approve, publish, sửa graph hay quản lý gap.

Nếu hệ thống đang bật local authentication, endpoint này cần owner session và CSRF hợp lệ.
Để test local theo runbook, dùng `AUTH_MODE=disabled`; không hạ auth ở môi trường dùng chung.

## 7. Cấu hình và chạy Discord gateway

Thêm vào `.env`, thay placeholder bằng giá trị thật:

```dotenv
DISCORD_BOT_TOKEN=<discord-bot-token>
DISCORD_RESEARCH_API_TOKEN=<research-service-account-token>
DISCORD_ALLOWED_GUILD_IDS=<server-id>
DISCORD_ALLOWED_CHANNEL_IDS=<channel-id>
DISCORD_INTAKE_NAMESPACE=discord
DISCORD_INTAKE_PROVIDER=mistral
DISCORD_AUTO_APPROVE_LINKS=true
DISCORD_LOCALE=vi
DISCORD_USER_RATE_LIMIT=10
DISCORD_POLL_INTERVAL_SECONDS=5
DISCORD_POLL_ATTEMPTS=36
```

Không chạy hoặc chia sẻ output của `docker compose config` sau khi đã điền secret vì lệnh đó
có thể render giá trị environment. Khởi động bot:

```bash
docker compose --profile discord up -d --build discord-bot
docker compose --profile discord ps discord-bot
docker compose logs --tail=100 discord-bot
```

Kết quả đạt:

- Container không restart loop.
- Log có `Discord gateway ready`.
- Bot hiện online trong server test.
- Presence của bot có gợi ý `/help`.
- Đủ bảy slash commands `/help`, `/guide`, `/sources`, `/ping`, `/pin`, `/submit`, `/status`
  xuất hiện. Discord có thể cần một khoảng ngắn để đồng bộ guild commands.

## 8. Bộ test nghiệm thu trên Discord

Mỗi test dùng một message riêng. Lưu lại message ID bằng Developer Mode, nhưng không lưu
token hoặc nội dung nhạy cảm.

### TC-01 — Message không có nguồn

Gửi một message thường, không có URL/PDF.

Kỳ vọng: bot không tạo receipt và trả thông báo không có nguồn để thu thập.

### TC-02 — Bài báo/public article

Gửi trực tiếp một public URL có nội dung đọc được — không gọi `/submit` — ví dụ một bài báo
kỹ thuật hoặc abstract công khai:

```text
https://arxiv.org/abs/2210.03629
```

Kỳ vọng:

1. Bot thêm reaction `⏳`.
2. Bot tự tạo receipt và trả đúng một summary theo từng item.
3. Kết quả cuối là một trong các trạng thái hợp lệ:
   - `✅` nếu nguồn đầy đủ, confidence đạt ngưỡng và đã được guarded auto-approval.
   - `📥` nếu hệ thống yêu cầu người duyệt.
   - `⚠️` nếu chỉ lấy được một phần nội dung.
4. Nếu `✅`, receipt có `research_id`; item xuất hiện trong relationship graph.
5. Nếu có active low-coverage gap liên quan, reply có phần
   **“Đã phát hiện khoảng trống tri thức”**.

Không coi `📥` là lỗi bot: guarded auto-approval cố ý từ chối nguồn thiếu dữ liệu hoặc
confidence thấp. Duyệt item tại `http://localhost:13000/ingestion`, rồi chạy
`/status message_id:<Discord-message-id>` để xem trạng thái mới và gap liên quan.

### TC-03 — Nhiều URL trong một message

Gửi hai public URL khác nhau trong cùng một message.

Kỳ vọng: chỉ có một receipt, có hai item theo đúng thứ tự; reply không che lỗi của item kém
nhất. Giới hạn hiện tại là 20 URL/message.

### TC-04 — Gửi lại cùng message

Dùng lại đúng Discord message ID qua event redelivery hoặc kiểm tra `/status` nhiều lần.
Nếu môi trường test không hỗ trợ redelivery, gửi lại cùng URL ở message mới để kiểm tra
deduplication research.

Kỳ vọng:

- Redelivery của cùng message không tạo công việc trùng.
- Cùng URL ở message mới vẫn tạo occurrence mới nhưng liên kết research đã có.
- Reply/reaction dùng `♻️` khi item được liên kết với dữ liệu đã thu thập.

### TC-05 — PDF attachment

Đính kèm một PDF có text, kích thước không quá 20 MB.

Kỳ vọng: file bytes được lưu qua API trước khi xử lý async; receipt có item `document`.
PDF scan không có OCR khả dụng phải báo limitation rõ ràng, không giả vờ thành công.
Giới hạn hiện tại là 5 file/message.

### TC-06 — Facebook Reel hoặc nguồn hạn chế

Gửi một Reel công khai thuộc danh mục hệ thống.

Kỳ vọng:

- Nếu lấy được metadata nhưng chưa có transcript, kết quả là `⚠️`/chờ review và nêu hành
  động cần transcript.
- Bot không vượt login, paywall, region lock hoặc anti-bot challenge.
- Khi có nguồn/transcript đủ và item được approve, graph/gap chạy như article.

Automatic Reel media download/transcription chưa nằm trong phạm vi hiện tại.

### TC-07 — Allowlist

Gửi URL từ một channel hoặc server không nằm trong allowlist.

Kỳ vọng: bot bỏ qua hoàn toàn, không reaction, không reply, không receipt.

### TC-08 — Slash commands

```text
/help
/guide
/sources
/ping
/pin message_id:<Discord-message-id-trong-channel-hien-tai>
/submit url:<public-url>
/status message_id:<Discord-message-id-da-test>
```

Kỳ vọng:

- `/help` liệt kê đủ bảy lệnh, nói rõ gửi link trực tiếp là đủ và `/submit` chỉ tùy chọn.
- `/guide` mô tả đúng luồng receipt → review → relationship graph → knowledge gap.
- `/sources` nêu article, paper, GitHub, Facebook/Reel, PDF cùng giới hạn
  20 link, 5 PDF và 20 MB/PDF.
- `/ping` trả gateway latency và không gọi API có đặc quyền.
- `/pin` ghim đúng message trong channel hiện tại và trả ephemeral response.
- `/submit` trả kết quả intake; `/status` tìm receipt theo message ID trong namespace
  `discord`.
- Các lệnh hướng dẫn và `/status` trả ephemeral response.
- Người dùng/channel ngoài allowlist không được dùng command để bypass giới hạn.

### TC-09 — Hướng dẫn khi mention

Mention bot trong một message không có URL/PDF.

Kỳ vọng: bot không tạo receipt; reply hướng người dùng tới `/help`. Presence của bot cũng
hiển thị gợi ý `/help`.

### TC-10 — Quyền ghim message

1. Chọn một message trong channel test, bật Developer Mode và copy Message ID.
2. Với user có **Pin Messages** và bot có **Pin Messages**, chạy:

   ```text
   /pin message_id:<id>
   ```

3. Chạy lại cùng lệnh.
4. Bỏ quyền **Pin Messages** của user test rồi thử lại.
5. Khôi phục user, bỏ quyền **Pin Messages** của bot rồi thử lại; sau đó khôi phục.
6. Thử ID của message thuộc channel khác.

Kỳ vọng:

- Lần đầu message được ghim và Discord audit log có pin event.
- Lần hai báo message đã ghim, không tạo mutation thứ hai.
- Thiếu quyền user hoặc bot đều bị từ chối bằng ephemeral response rõ ràng.
- ID ở channel khác không được tìm thấy; bot không tìm chéo channel.
- Không có Research API/service-account/graph permission nào được thêm.

## 9. Chứng minh receipt, graph và knowledge gap

### 9.1 Đọc receipt bằng scoped token

Nhập token bằng hidden prompt để token không nằm trong shell history:

```bash
read -rsp 'Research service token: ' BOT_RESEARCH_TOKEN
echo
read -rp 'Discord message ID: ' DISCORD_MESSAGE_ID
curl -fsS -G \
  http://localhost:18000/api/v1/intake/receipts \
  -H "Authorization: Bearer ${BOT_RESEARCH_TOKEN}" \
  --data-urlencode "occurrence_ref=${DISCORD_MESSAGE_ID}" \
  | jq '{
      id,
      status,
      replayed,
      delivery_count,
      items: [.items[] | {
        kind,
        disposition,
        status,
        review_status,
        research_id,
        error_code,
        knowledge_gaps
      }]
    }'
unset BOT_RESEARCH_TOKEN
```

Không bật `set -x` trong terminal đang giữ token.

### 9.2 Kiểm tra graph

Mở `http://localhost:13000/graph`, chọn **Relationship**, rồi tìm title/tag của item.
Hoặc dùng API:

```bash
read -rp 'Từ khóa title/tag cần tìm: ' GRAPH_QUERY
curl -fsS -G http://localhost:18000/api/v1/graph \
  --data-urlencode 'view=relationship' \
  --data-urlencode "query=${GRAPH_QUERY}" \
  | jq '{node_count: (.nodes | length), edge_count: (.edges | length), nodes}'
```

Kết quả đạt khi item approved có node/evidence liên quan trong relationship graph.
Hierarchy placement, nếu được AI đề xuất, nằm tại `http://localhost:13000/graph/changes`
để người duyệt apply; bot không tự apply change set.

### 9.3 Kiểm tra knowledge gap

```bash
curl -fsS http://localhost:18000/api/v1/gaps \
  | jq '[.[] | select(
      .status == "detected" or
      .status == "prioritized" or
      .status == "assigned"
    )]'
```

Bot chỉ thông báo gap đang active và liên quan trực tiếp tới item approved trong receipt.
Không có alert là hợp lệ nếu concept đã đủ coverage, item chưa approved, hoặc gap đã
dismiss/snooze/fill. Dùng `/status` và trường `items[].knowledge_gaps` để phân biệt trường
hợp “không có gap” với “pipeline chưa hoàn tất”.

## 10. Bảng trạng thái mong đợi

| Dấu hiệu | Ý nghĩa | Hành động tester |
| --- | --- | --- |
| `⏳` | Đã nhận, đang xử lý | Chờ tối đa poll budget đã cấu hình |
| `✅` | Đã publish vào knowledge base | Kiểm tra `research_id`, graph và gap |
| `📥` | Cần người duyệt | Duyệt ở `/ingestion`, sau đó dùng `/status` |
| `⚠️` | Nguồn chỉ xử lý được một phần | Đọc limitation/action trong reply |
| `♻️` | Liên kết dữ liệu đã có | Xác nhận không tạo research trùng |
| `❌` | Xử lý thất bại | Kiểm tra error code và logs |
| `🚫` | Vượt rate limit hoặc không được phép | Chờ cửa sổ rate limit/kiểm tra allowlist |

## 11. Troubleshooting

| Triệu chứng | Kiểm tra |
| --- | --- |
| Container thoát ngay | Bốn biến bắt buộc có giá trị; guild/channel allowlist không rỗng |
| Discord đóng kết nối với code `4014` | Bật Message Content Intent trong Developer Portal rồi restart bot |
| Bot online nhưng không đọc message | Channel ID/server ID, View Channel, Message Content Intent |
| Không reaction hoặc reply | Add Reactions, Send Messages, Read Message History; xem log bot/API/worker |
| Không thấy slash command | Scope `applications.commands`, đúng guild install; restart và chờ guild sync |
| `/pin` báo thiếu quyền | Cấp `Pin Messages` cho đúng user role và bot role tại chính channel; không dùng Administrator |
| API trả `401/403` | Token chưa revoke, namespace `discord`, đủ `intake:submit` và `intake:read-own` |
| `⏳` quá ba phút | Kiểm tra `worker`, provider preflight và `/status`; poll hết hạn không đồng nghĩa job bị mất |
| Article luôn `📥` | Đọc confidence/completeness; guarded approval cố ý yêu cầu review khi không đủ chuẩn |
| Reel `⚠️` | Thường là metadata-only/transcript thiếu; đây là boundary đã công bố |
| Không có gap alert | Item chưa approved hoặc không có active low-coverage gap liên quan; kiểm tra receipt |
| Provider preflight lỗi | Key/model/network/egress của provider; không đổi sang mock |

Thu log giới hạn để chẩn đoán:

```bash
docker compose logs --tail=200 discord-bot api worker
```

Không đăng nguyên log ra nơi công khai trước khi kiểm tra dữ liệu người dùng và header nhạy cảm.

## 12. Cleanup và revoke

1. Dừng bot:

   ```bash
   docker compose --profile discord stop discord-bot
   ```

2. Revoke service account bằng `id` đã lưu:

   ```bash
   read -rp 'Service account ID cần revoke: ' SERVICE_ACCOUNT_ID
   curl -fsS -X DELETE \
     "http://localhost:18000/api/v1/auth/service-accounts/${SERVICE_ACCOUNT_ID}"
   ```

3. Xóa hai token Discord khỏi `.env`. Nếu token từng lộ, reset Discord bot token.
4. Giữ database nếu cần review evidence. Chỉ chạy `docker compose down -v` khi chủ động
   muốn xóa toàn bộ volume/test data.

## 13. Checklist nghiệm thu

- [ ] Gate 1 pass.
- [ ] Bot chỉ hoạt động trong guild/channel allowlist.
- [ ] Public article tạo receipt và đạt `✅`, hoặc `📥` với lý do review hợp lệ.
- [ ] Item approved có `research_id` và xuất hiện trong relationship graph.
- [ ] Khi receipt có active related gap, bot thông báo gap tại channel.
- [ ] Duplicate không tạo research trùng.
- [ ] PDF và Reel trả đúng success/partial/review boundary.
- [ ] Gửi link thường tự tạo intake; không cần `/submit`.
- [ ] Đủ bảy slash commands hiển thị; `/help`, `/guide`, `/sources`, `/ping` trả đúng nội dung.
- [ ] `/pin` pass success, idempotent, caller-denied, bot-denied và cross-channel-denied.
- [ ] Mention không kèm nguồn và presence đều giúp người dùng tìm thấy `/help`.
- [ ] Bot không có quyền approve, graph mutation hoặc gap management.
- [ ] Service account đã revoke sau test.
- [ ] Evidence không chứa secret hoặc dữ liệu nhạy cảm.

Evidence nên lưu: thời gian test, commit SHA, Discord message ID, receipt ID, research ID,
trạng thái cuối, số node/edge tìm thấy và gap ID. Không lưu token.

## 14. Tài liệu liên quan

- `apps/discord-bot/README.md`
- `Docs/Intake Occurrence and Receipt Specification.md`
- `Docs/Research System Completion Plan.md`
- [Discord application quick start](https://docs.discord.com/developers/quick-start/getting-started)
- [Discord Gateway và privileged intents](https://docs.discord.com/developers/events/gateway)
- [Discord OAuth2 scopes và permissions](https://docs.discord.com/developers/platform/oauth2-and-permissions)
- [Cách lấy Server/Channel/Message ID](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID)
