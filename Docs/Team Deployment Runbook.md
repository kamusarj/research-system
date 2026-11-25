# Runbook triển khai cho nhóm nghiên cứu

Tài liệu này hướng dẫn đưa Hệ thống nghiên cứu từ chế độ cục bộ một người dùng sang bản triển khai
dùng chung cho cả nhóm: bắt buộc đăng nhập, phân quyền theo vai trò, truy cập qua HTTPS và có sao lưu.

## 1. Kiến trúc

```text
Thành viên (trình duyệt, HTTPS)
        │
        ▼
Lối vào HTTPS ── Caddy (hồ sơ `https`) hoặc Cloudflare Tunnel (hồ sơ `tunnel`)
        │
        ▼
frontend  Next.js standalone, chỉ nghe 127.0.0.1:FRONTEND_PORT trên máy chủ
        │  /api/v1/* được proxy nội bộ
        ▼
api       FastAPI (AUTH_MODE=local, DEPLOYMENT_ENVIRONMENT=production), không mở cổng ra ngoài
        │
        ├── database  PostgreSQL + pgvector (không mở cổng)
        └── worker    xử lý hàng đợi liên kết và tài liệu
```

Khác biệt so với chế độ cục bộ (`docker-compose.yml` + `docker-compose.multi-user.yml`):

| | Cục bộ | Nhóm (`docker-compose.team.yml`) |
| --- | --- | --- |
| Đăng nhập | Tắt, mọi người là chủ sở hữu | Bắt buộc, cookie `__Host-` + Secure + CSRF |
| Mã nguồn | Bind-mount từ thư mục repo | Đóng gói trong ảnh, không reload |
| Cổng API | Mở `18000` | Không mở; chỉ qua proxy Next.js |
| Truy cập | `http://localhost:13000` | `https://<PUBLIC_URL>` |
| Giới hạn tần suất | Theo IP kết nối | Theo từng tài khoản; đăng nhập theo IP thật |

Hai chế độ dùng chung tên dự án Compose `businessaiagents` nên **dùng chung dữ liệu**: chuyển sang
chế độ nhóm giữ nguyên nghiên cứu, tài liệu và đồ thị hiện có.

## 2. Yêu cầu

- Docker Engine và Docker Compose v2.24 trở lên (file dùng `!reset`/`!override`).
- Máy chủ tối thiểu 4 GB RAM trống cho stack, khoảng 8 GB đĩa trống khi build ảnh lần đầu
  (ảnh API chứa TeX/OCR khoảng 4,5 GB).
- Khóa nhà cung cấp AI dùng chung cho cả nhóm (mặc định Mistral cho phân loại/RAG, DeepSeek cho
  trò chuyện đồ thị). Thành viên có thể tự nhập API cá nhân trong trang Trò chuyện.

## 3. Chuẩn bị `.env.team`

```bash
cp .env.team.example .env.team
chmod 600 .env.team
```

Điền tối thiểu:

| Biến | Ý nghĩa |
| --- | --- |
| `PUBLIC_URL` | Địa chỉ thành viên mở, luôn `https://...` |
| `POSTGRES_PASSWORD` | Chỉ gồm chữ và số, ví dụ `openssl rand -hex 24` |
| `COMPOSE_PROFILES` | `https` (Caddy), `tunnel` (Cloudflare Tunnel) hoặc để trống |
| `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY` | Khóa AI dùng chung (hoặc cấp qua `/run/secrets`) |

`.env.team` đã nằm trong `.gitignore`. Không chép giá trị bí mật vào `AI_LOGS/` hay tài liệu.
Mọi biến trong `.env.example` đều dùng được trong `.env.team` khi cần đổi mặc định.

API/worker chạy UID/GID `10001:10001`, hệ tệp gốc và mã nguồn chỉ đọc, không capabilities hay nâng
quyền. Chỉ named volume tài liệu và `/tmp` tmpfs (512 MiB mỗi container) được ghi. Khi khởi động,
`document-storage-init` chạy một lần để chuẩn bị quyền volume cũ/mới, không đổi nội dung/mode và
không theo symlink. Bước này không có mạng, biến môi trường hoặc secret của ứng dụng.

API/worker giới hạn 256 tiến trình/luồng mỗi container (init: 64). LaTeX dùng giới hạn cgroup
hữu hạn này để tránh xung đột với số luồng API theo cùng UID; các giới hạn CPU/RAM/tệp/timeout
và chế độ không shell escape vẫn được giữ.

Nếu dùng `/run/secrets` qua Compose bind-mount, tệp trên máy chủ phải cho GID 10001 đọc. Giữ owner
là root hoặc chủ sở hữu, đặt nhóm 10001 và mode `0640` (thư mục chứa vẫn riêng tư); không dùng
`0644`/`0777`. Compose local không áp dụng `uid`/`gid` khai báo trong secret khi nguồn là file.
Ví dụ, với một đường dẫn do người vận hành chọn:

```bash
sudo chgrp 10001 /duong-dan-rieng/openai_api_key
sudo chmod 0640 /duong-dan-rieng/openai_api_key
```

Kiểm tra cấu hình: `make team-config`.

## 4. Chọn lối vào HTTPS

Cookie phiên là `Secure`, nên **thành viên phải truy cập bằng HTTPS**; mở bằng `http://` sẽ đăng
nhập không giữ được phiên (giao diện báo rõ lỗi này).

### 4a. Cloudflare Tunnel (khuyến nghị khi thành viên ở nhiều nơi)

1. Trong Cloudflare Zero Trust, tạo tunnel và một Public Hostname, ví dụ `research.example.com`,
   dịch vụ `http://frontend:3000`.
2. Trong `.env.team`: `COMPOSE_PROFILES=tunnel`, `CLOUDFLARE_TUNNEL_TOKEN=<token>`,
   `PUBLIC_URL=https://research.example.com`.
3. Không cần mở cổng nào trên máy chủ. Có thể bật thêm Cloudflare Access để giới hạn email nhóm.

### 4b. Caddy với tên miền công khai

1. Trỏ bản ghi DNS A/AAAA của tên miền về máy chủ; mở cổng 80 và 443.
2. Trong `.env.team`: `COMPOSE_PROFILES=https`, `SITE_ADDRESS=research.example.com`,
   `PUBLIC_URL=https://research.example.com`. Caddy tự xin chứng chỉ Let's Encrypt.

### 4c. Caddy trong mạng nội bộ (LAN)

1. `SITE_ADDRESS=192.168.1.20` (IP LAN của máy chủ), `PUBLIC_URL=https://192.168.1.20`.
2. Caddy dùng CA nội bộ; mỗi thành viên cài chứng chỉ gốc một lần:

   ```bash
   docker compose --env-file .env.team -f docker-compose.yml -f docker-compose.team.yml \
     exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt
   ```

### 4d. Reverse proxy riêng hoặc Tailscale

Để trống `COMPOSE_PROFILES`; trỏ proxy của bạn tới `FRONTEND_BIND:FRONTEND_PORT`. Nếu proxy ở máy
khác, đặt `FRONTEND_BIND` thành IP nội bộ phù hợp (không dùng `0.0.0.0` khi máy có IP công khai).

## 5. Khởi động lần đầu

### Từ dữ liệu cục bộ hiện có

```bash
make team-backup                 # sao lưu trước khi chuyển (xem mục 8)
make team-db-password            # đổi mật khẩu PostgreSQL cũ `research` theo POSTGRES_PASSWORD
make team-up                     # build ảnh production, chạy migration, kiểm tra tự động
```

`make team-db-password` cần thiết vì `POSTGRES_PASSWORD` chỉ áp dụng khi volume được tạo lần đầu.

### Máy chủ mới

```bash
make team-up
```

`make team-up` build ảnh `api` và `frontend`, khởi động mọi dịch vụ (kể cả hồ sơ trong
`COMPOSE_PROFILES`), chờ healthcheck rồi chạy `scripts/team.sh verify`: dịch vụ đang chạy, API không
mở cổng, `auth/config` báo `enabled=true` và API dữ liệu trả `401` khi chưa đăng nhập.

### 5a. Kết nối model local

Mẫu `.env.team.example` đã khai báo hai URL cầu nối. Khi cần dùng, thêm `local-ai` vào hồ sơ lối vào
đang chọn, ví dụ `COMPOSE_PROFILES=https,local-ai` hoặc `tunnel,local-ai`. Nếu có reverse proxy riêng,
dùng `COMPOSE_PROFILES=local-ai`. Giữ nguyên các cấu hình đăng nhập/HTTPS của bản nhóm.

**Model cùng máy chủ Linux:** mở Ollama trên `127.0.0.1:11434` hoặc LM Studio trên
`127.0.0.1:1234`, dùng model đã cài. Trong `.env.team`, đặt `OLLAMA_MODEL` hoặc
`LOCAL_OPENAI_MODEL` thành đúng định danh từ runtime model. Không cần đổi provider mặc định để
chọn model trong Trò chuyện. AI tác vụ nền chỉ đổi khi operator chủ động đặt
`AI_PROVIDER=ollama|local_openai`.

API/worker gọi `OLLAMA_BASE_URL=http://172.17.0.1:11435` hoặc
`LOCAL_OPENAI_BASE_URL=http://172.17.0.1:11437/v1`. Bridge chuyển tiếp tới
`OLLAMA_BRIDGE_UPSTREAM=http://127.0.0.1:11434` hoặc
`LOCAL_OPENAI_BRIDGE_UPSTREAM=http://127.0.0.1:1234`.

`172.17.0.1` là ví dụ mặc định của Linux Docker, không phải IP máy cá nhân. Kiểm tra địa chỉ bridge
trên máy deploy bằng `docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'`;
nếu khác, đổi cả `*_BRIDGE_BIND` và host trong `*_BASE_URL` tương ứng. Không bind bridge vào IP
công khai. Các service `network_mode: host` này cần máy Linux có địa chỉ bridge truy cập được từ
container; Docker Desktop cần cấu hình mạng tương đương hoặc endpoint VPN riêng.

Sau khi đã đủ đĩa để build ảnh nhóm:

```bash
make team-config
make team-up
docker compose --env-file .env.team -f docker-compose.yml -f docker-compose.team.yml \
  --profile local-ai exec -T api python - <<'PY'
from app.services.providers.local_models import list_local_models
for provider in ("ollama", "local_openai"):
    try:
        print(provider, "installed_models=", len(list_local_models(provider)))
    except Exception as error:
        print(provider, "error=", getattr(error, "code", type(error).__name__))
PY
```

Không cấu hình cả hai runtime cũng được; runtime không dùng sẽ báo chưa kết nối. Trong **Trò chuyện**,
chọn Ollama hoặc model local tương thích OpenAI, tải danh sách và kiểm tra model, rồi tạo cuộc trò
chuyện. Phép kiểm tra này mới thực hiện inference; danh mục có model chưa chứng minh model trả lời
được JSON. Model được giữ cố định theo phiên. Embedding vẫn dùng cấu hình riêng hiện có.

**Model trên máy cá nhân, ứng dụng ở máy chủ khác:** xem recipe reverse SSH và VPN tại
[kế hoạch local model](Local%20Model%20Deployment%20Plan.md#recipe-model-trên-máy-cá-nhân).
Giữ máy cá nhân và tunnel hoạt động; mất kết nối sẽ báo lỗi, không tự chuyển cloud.

### Tự khởi động sau khi máy khởi động lại

Container dùng `restart: unless-stopped`. Nếu đã cài dịch vụ người dùng `business-ai-agents.service`,
cài lại script để nó nhận biết chế độ nhóm (có `.env.team` thì chạy bản nhóm, ngược lại chạy bản cục bộ):

```bash
install -Dm755 scripts/start_local_autostart.sh ~/.local/bin/business-ai-agents-autostart
systemctl --user restart business-ai-agents.service
scripts/verify_local_autostart.sh
```

## 6. Tài khoản và phân quyền

Tạo chủ sở hữu đầu tiên (mật khẩu nhập ẩn, tối thiểu 12 ký tự):

```bash
make team-owner NAME="Linh" EMAIL=linh@example.com
```

Sau đó đăng nhập và vào **Quản trị → Thành viên** (`/members`) để tạo tài khoản cho thành viên với
mật khẩu tạm ngẫu nhiên, đổi vai trò, khóa tài khoản hoặc đặt lại mật khẩu. Gửi mật khẩu tạm qua
kênh riêng; thành viên tự đổi ở **Tài khoản** (`/account`), thao tác này đăng xuất các thiết bị khác.
Có thể tạo nhà nghiên cứu từ terminal: `make team-member NAME="An" EMAIL=an@example.com`.

| Vai trò | Được làm |
| --- | --- |
| Người xem (`viewer`) | Đọc thư viện, đồ thị, tài liệu; tìm kiếm; đổi mật khẩu của mình |
| Nhà nghiên cứu (`researcher`) | Thêm liên kết/tài liệu, soạn và sửa bản nháp, trò chuyện AI, đề xuất thay đổi đồ thị, quét khoảng trống, chạy nguồn RSS |
| Chủ sở hữu (`owner`) | Mọi quyền trên, cộng: duyệt/xuất bản nghiên cứu và liên kết (kể cả duyệt hàng loạt), sửa nghiên cứu đang duyệt/đã xuất bản, quyết định và áp dụng thay đổi đồ thị, cấu hình nguồn RSS, xóa, quản lý thành viên và tài khoản dịch vụ |

Chỉ chủ sở hữu và tài khoản dịch vụ tiếp nhận (ví dụ cổng Discord) được yêu cầu tự duyệt; yêu cầu
tự duyệt từ nhà nghiên cứu được bỏ qua và nguồn vào hàng chờ duyệt.

Lưu ý dữ liệu dùng chung: lịch sử trò chuyện, thư viện và đồ thị là tài sản chung của nhóm; mọi
thành viên đăng nhập đều xem được. Không đưa dữ liệu cá nhân nhạy cảm vào hệ thống.

## 7. Vận hành hằng ngày

```bash
make team-ps                     # trạng thái
make team-logs                   # nhật ký JSON (Ctrl+C để thoát)
scripts/team.sh logs worker      # nhật ký một dịch vụ
make team-verify                 # kiểm tra nhanh
make team-down                   # dừng (không xóa dữ liệu)
```

Cập nhật phiên bản mới: lấy mã mới rồi `make team-up` (migration chạy tự động khi API khởi động).

Trên máy thiếu đĩa, có thể tái sử dụng ảnh dependency đã kiểm chứng, còn chạy root. Nếu lockfile
đã đổi (ví dụ bản vá Python), cập nhật package trên lớp TeX/OCR cũ trước khi build runtime:

```bash
docker build --target refresh-dependencies \
  --build-arg API_REUSE_BASE=businessaiagents-api:verified-root-base \
  -t businessaiagents-api-dependencies:verified apps/api
docker compose build --build-arg API_DEPENDENCIES_IMAGE=businessaiagents-api-dependencies:verified api worker
```

Tên `verified-root-base` phải là ảnh có sẵn đã kiểm chứng; không gắn nhãn này cho runtime non-root.
Ảnh dependency đầu ra phải có SHA-256 của `/app/uv.lock` trùng `apps/api/uv.lock` và
`python -m pip check` sạch. Build mặc định vẫn cài dependency từ lockfile;
không tái sử dụng ảnh runtime đã tạo tài khoản 10001 làm dependency base. Trước khi áp dụng, chạy
`bash scripts/verify_container_hardening.sh` với ảnh mới; tùy chọn `--live` kiểm tra thêm hai
container cục bộ (chỉ tạo/xóa fixture tạm).

## 8. Sao lưu và khôi phục

```bash
make team-backup
```

Tạo `~/business-ai-agents-backups/<thời-điểm>/` (quyền 700) gồm `postgres.dump` (định dạng custom,
đã kiểm tra bằng `pg_restore --list`), `document-objects.tar.gz` và manifest SHA-256. Backup thủ công
và timer dùng chung engine: luôn dừng API/worker đang chạy trong cả hai bước dump/tar, rồi khởi động
lại đúng các dịch vụ đó kể cả khi gặp lỗi. Trong lúc backup, thao tác ghi và ứng dụng có thể tạm
gián đoạn; không có tùy chọn bỏ quiesce. Giữ 14 bản hoàn tất gần nhất có manifest của engine;
không xóa thư mục rollback/thủ công không được engine nhận dạng. Có thể đặt
`BACKUP_DIR=/đường/dẫn`, `BACKUP_KEEP=30`; `TEAM_ENV_FILE` chọn file env nhóm khác.
Cài timer người dùng cho cả local hoặc team:

```bash
scripts/install_backup_timer.sh
systemctl --user start business-ai-agents-backup.service  # chạy thử ngay
systemctl --user list-timers business-ai-agents-backup.timer
loginctl enable-linger "$USER"  # cho phép timer chạy cả khi đăng xuất
```

Timer chạy 02:30 giờ máy, chạy bù sau khi bật máy. Script cài ngoài repo, dừng API/worker đang chạy,
kiểm tra dump/tar, ghi manifest SHA-256 rồi khởi động lại đúng các dịch vụ đó cả khi gặp lỗi.
Thư mục `~/business-ai-agents-backups/scheduled/` chỉ giữ 14 bản hoàn tất do script này tạo;
không xóa bản thủ công. Xem lỗi bằng `journalctl --user -u business-ai-agents-backup.service`.
Nếu đổi mã script, chạy lại installer. Không cài thêm cron trùng lịch.

Sao chép thư mục sao lưu ra ổ/dịch vụ khác. Khóa API nằm trong `.env.team`/secret, cần sao lưu riêng.

Khôi phục dùng helper có kiểm tra lỗi, chỉ hỗ trợ bản backup local có manifest của engine. Trước
khi bảo trì, giữ một bản backup hiện trạng đã xác minh ở vị trí riêng để có đường quay lại. Kiểm
tra bản định khôi phục trước (không dừng dịch vụ hoặc ghi đè dữ liệu):

```bash
RESTORE_FROM=/đường/dẫn/backup make team-restore
```

Helper kiểm hash/kích thước của cả dump và tar, từ chối đường dẫn thoát thư mục, link và entry đặc
biệt/trùng lặp; kiểm catalogue PostgreSQL và dung lượng đủ để giải nén vào staging. Database phải
đang chạy; ảnh worker phải có sẵn. Phép kiểm tra tạo container tạm không có dependency để đọc dung
lượng volume, không khởi động ứng dụng. MinIO cần quy trình khôi phục và kiểm chứng riêng.

Chỉ khi đã quyết định bảo trì và chấp nhận thay thế dữ liệu hiện tại:

```bash
RESTORE_FROM=/đường/dẫn/backup RESTORE_APPLY=1 make team-restore
```

Khôi phục dùng lock chung với backup, dừng API/worker/frontend, giải nén vào thư mục staging riêng
trước khi thay database. PostgreSQL dùng `--single-transaction` (bao gồm dừng khi SQL lỗi). Sau đó
helper đổi tệp từ staging, chạy migration/parity và kiểm tham chiếu/hash tệp cùng invariant đồ thị
khi ứng dụng còn dừng; chỉ khởi động lại các dịch vụ vốn đang chạy sau khi mọi kiểm tra đạt. Nếu
frontend được khởi động lại, còn kiểm health/xác thực và dữ liệu ẩn danh phải trả401.
Tệp trước khôi phục được giữ đến khi cả kiểm tra chạy thật đạt; helper chỉ dọn chúng cuối cùng.

**Bất kỳ lỗi nào sau khi bắt đầu bảo trì đều không tự resume**; helper cố dừng cả ba dịch vụ,
trả exit1 và tên bước lỗi. Transaction chỉ bảo vệ PostgreSQL, không tạo transaction chung với tệp.
Nếu lỗi ở bước đổi tệp/migration/smoke, database có thể đã khôi phục và volume có thể chứa staging
hoặc `.restore-previous-*`; giữ ứng dụng dừng, không chạy autostart/team-up/timer backup cho đến khi
operator kiểm tra. Tắt lịch backup/autostart trong cửa sổ khôi phục và bật lại sau nghiệm thu.
Không tự xóa các thư mục `.restore-*`: bảo toàn chúng để phục hồi hoặc kiểm tra rồi xử lý thủ công;
helper từ chối một lần khôi phục mới khi còn thư mục này. Nếu cần quay lại, dùng bản backup trước
bảo trì đã xác minh sau khi làm rõ trạng thái database/tệp. Chỉ lần thành công mới dọn bản tệp cũ.

`TEAM_ENV_FILE` chọn env nhóm khác. Nếu dùng overlay secret, cấp cùng file cho helper:
`RESTORE_COMPOSE_FILE=docker-compose.secrets.example.yml` (kèm các biến đường dẫn secret như lúc
triển khai). Hoặc gọi `python3 scripts/restore_local.py --repo "$PWD" --env-file .env.team
--backup /đường/dẫn/backup --compose-file /đường/dẫn/overlay.yml`; thêm `--apply` chỉ trong bảo trì.
Không có flag apply thì chỉ kiểm tra. Không dùng lại chuỗi lệnh restore rời rạc bỏ qua exit code.
Với stack cục bộ, có thể bỏ `--env-file`: helper tự chọn `.env.team` nếu có, nếu không dùng cùng
base/multi-user và project local với backup timer. Không đổi chế độ xác thực khi kiểm/khôi phục;
smoke local đối chiếu cấu hình xác thực hiện có. Timer từ chối xuất bản một backup mới nếu volume
còn `.restore-*`, tránh nhận nhầm staging chưa hoàn tất thành một bản sao lưu dùng được.

Diễn tập vào môi trường tách biệt theo `Docs/Graph Intelligence v2 Operations Runbook.md`; bản vá
này được kiểm bằng fixture, không có quyền tự restore ghi đè database thật của người dùng.

## 9. Xử lý sự cố

| Hiện tượng | Nguyên nhân và cách xử lý |
| --- | --- |
| Đăng nhập xong vẫn quay lại màn đăng nhập / báo "Trình duyệt chưa lưu phiên" | Đang mở bằng `http://`. Dùng đúng `PUBLIC_URL` dạng `https://`. |
| `make team-up` báo thiếu `PUBLIC_URL`/`POSTGRES_PASSWORD` | Điền `.env.team`; mật khẩu chỉ chữ/số, khác `research`. |
| API không khởi động, log `password authentication failed` | Volume cũ còn mật khẩu `research`: chạy `make team-db-password`. |
| Caddy không lấy được chứng chỉ | DNS chưa trỏ đúng hoặc cổng 80/443 bị chặn/đang dùng; đổi `HTTP_PORT`/`HTTPS_PORT` chỉ hợp lệ khi có proxy khác phía trước. |
| "Đã chạm giới hạn tần suất" | Mặc định mỗi tài khoản 30 lượt trò chuyện, 10 lượt phân tích/tải lên mỗi phút; đăng nhập 10 lần/phút/IP. Chỉnh `RATE_LIMIT_*`. Giới hạn đếm theo từng tiến trình API (`API_WORKERS`). |
| Liên kết/tài liệu báo "Tác vụ bị gián đoạn nhiều lần" | Worker bị dừng giữa chừng quá số lượt thử (thiếu RAM, khởi động lại). Kiểm tra `scripts/team.sh logs worker`, rồi bấm Thử lại. |
| Hết đĩa khi build | Ảnh API lớn; dọn image/build cache không dùng (`docker image prune`, `docker builder prune`) sau khi kiểm tra kỹ. |

## 10. Giới hạn hiện tại

- Bộ giới hạn tần suất và chỉ số Prometheus nằm trong bộ nhớ từng tiến trình; đủ cho nhóm nhỏ, cần
  Redis/cổng API dùng chung nếu mở rộng nhiều máy.
- Chưa có SSO; tài khoản quản lý cục bộ bằng email/mật khẩu (Argon2).
- Bảng `outbox_events` mới chỉ được ghi; bản chiếu tìm kiếm Meilisearch/pgvector/Neo4j cho nghiên cứu
  đã duyệt vẫn cần chủ sở hữu bấm dựng lại khi bật các nhà cung cấp đó.
- Chuẩn hóa nhãn/tag hiện bỏ dấu tiếng Việt khi tạo khóa, nên hai nhãn chỉ khác dấu có thể bị gộp.
