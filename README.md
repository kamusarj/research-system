# Hệ thống nghiên cứu — MVP

Kho tri thức nghiên cứu về tác nhân AI cho doanh nghiệp, ưu tiên chạy cục bộ. Phần triển khai bám theo `Docs/Research System Implementation Plan.md`, dùng PostgreSQL làm nguồn dữ liệu chuẩn trong môi trường thật và cho phép SQLite để kiểm thử cục bộ nhanh.

Ngôn ngữ sản phẩm là tiếng Việt. Xem cách dùng thuật ngữ tại [`Docs/Quy uoc ngon ngu tieng Viet.md`](Docs/Quy%20uoc%20ngon%20ngu%20tieng%20Viet.md).

## Cấu trúc kho mã

```text
.
├── apps/
│   ├── api/                 # Ứng dụng FastAPI, migration và kiểm thử API
│   └── web/                 # Ứng dụng Next.js và thành phần giao diện dùng chung
├── Docs/                    # Tài liệu sản phẩm, kiến trúc và triển khai
├── AI_LOGS/                 # Bàn giao, quyết định, tác vụ và phiên làm việc giữa các tác nhân
├── docker-compose.yml       # Điều phối môi trường chạy cục bộ
├── Makefile                 # Các lệnh phát triển ổn định
└── README.md                # Điểm bắt đầu của kho mã
```

Mã ứng dụng nằm trong `apps/`. Thư mục gốc chỉ chứa tài liệu dùng chung, quy ước cho tác nhân AI và điểm vào để phát triển/vận hành. Xem `apps/README.md` để biết ranh giới từng mô-đun.

## Chạy bằng Docker

Yêu cầu: Docker có Compose. Bộ kiểm thử tương tác Playwright không bắt buộc nhưng cần Chrome hoặc Chromium.

```bash
cp .env.example .env
docker compose up --build
```

Nếu các cổng trên máy đã được dùng, có thể đổi cổng ngoài mà không đổi cổng trong container:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up --build
```

### Tự khởi động sau khi đăng nhập máy

Máy này lưu kho mã tại `$HOME/Desktop/Business AI Agents`. Chính sách `unless-stopped` của Docker khôi phục container hiện có khi daemon khởi động. Dịch vụ người dùng bên dưới sẽ thử bật lại bốn dịch vụ lõi sau khi phiên desktop bắt đầu, với giao diện ở cổng `13000` và API ở cổng `18000`:

```bash
install -Dm755 scripts/start_local_autostart.sh ~/.local/bin/business-ai-agents-autostart
install -Dm644 ops/systemd/user/business-ai-agents.service \
  ~/.config/systemd/user/business-ai-agents.service
systemctl --user daemon-reload
systemctl --user enable --now business-ai-agents.service
scripts/verify_local_autostart.sh
```

Các dịch vụ Compose cũng dùng `restart: unless-stopped`, tương tự bản Smart Exam cục bộ ở cổng `8080`. Có thể tắt tự khởi động mà không xóa container hoặc dữ liệu bằng:

```bash
systemctl --user disable --now business-ai-agents.service
```

Trình khởi chạy dùng `docker-compose.multi-user.yml`: bốn worker Uvicorn có thể cấu hình, nhóm kết nối PostgreSQL có giới hạn và máy chủ Next.js production độc lập. Chạy thủ công cùng chế độ bằng:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
  docker compose -f docker-compose.yml -f docker-compose.multi-user.yml \
  up -d --build database api worker frontend
scripts/verify_graph_multi_user.sh
```

Phản hồi đồ thị lớn hơn 1 KiB được nén; thao tác đọc đồ thị dùng bộ nhớ tạm riêng trong trình duyệt 30 giây; giao diện tái sử dụng kết quả truy vấn thay vì tải lại mỗi khi cửa sổ được chọn. Cổng chỉ nghe trên `127.0.0.1`; không mở bộ dịch vụ cục bộ cho máy khác khi còn tắt xác thực. Bản triển khai dùng chung phải bật xác thực/TLS theo hướng dẫn vận hành và đặt cổng tin cậy hoặc bộ giới hạn Redis dùng chung ở phía trước, vì bộ giới hạn tích hợp chỉ có hiệu lực trong từng tiến trình.

- Giao diện web: <http://localhost:3000>
- Tài liệu API: <http://localhost:8000/docs>
- Kiểm tra sức khỏe: <http://localhost:8000/api/v1/health>
- Trao đổi ý tưởng có kiểm soát trên đồ thị: <http://localhost:3000/chat>

Nạp dữ liệu mẫu vào cơ sở dữ liệu API đang chạy:

```bash
docker compose exec api python -m app.seed
```

### Dùng mô hình Ollama có sẵn trên máy từ Docker

Hồ sơ tùy chọn `local-ai` chỉ mở các điểm cuối thẻ, phiên bản và sinh nội dung của Ollama cho Docker qua địa chỉ nội bộ `docker0`; nó không kéo ảnh hay tải mô hình. Trước tiên hãy cài/chạy Ollama trên máy, đặt `OLLAMA_MODEL` thành mô hình đã xuất hiện trong `ollama list`, rồi khởi động cầu nối và tạo lại API/worker:

```bash
docker compose --profile local-ai up -d --build ollama-bridge api worker
```

Địa chỉ cầu nối mặc định là `172.17.0.1:11435`; container cục bộ truy cập được nhưng đây không phải địa chỉ LAN của máy. Đổi `OLLAMA_BRIDGE_BIND` nếu cầu Docker dùng địa chỉ khác. Cầu nối chủ động từ chối thao tác kéo mô hình và các đường dẫn Ollama tùy ý.

### Dùng quota Claude Code, Codex hoặc Antigravity thay cho API

Nếu máy đã đăng nhập `claude`, `codex` hoặc `agy` bằng gói đăng ký, API/worker có thể dùng quota đó thay cho API trả phí (chỉ chế độ cục bộ một chủ máy; chế độ nhóm luôn tắt, xem DEC-062). Cần `bubblewrap` và `xdg-dbus-proxy` trên máy:

```bash
scripts/install_ai_cli_bridge.sh   # cài user service, tạo token, ghi AI_CLI_BRIDGE_URL/TOKEN vào .env
# đặt AI_PROVIDER và GRAPH_CHAT_DEFAULT_PROVIDER = claude_code | codex | antigravity trong .env
systemctl --user restart business-ai-agents.service
```

Cầu nối `apps/api/app/ai_cli_bridge.py` chỉ nghe `172.17.0.1:11436` và đòi Bearer token. Claude Code chạy không có công cụ nào; Codex và Antigravity (vốn luôn có công cụ) chạy trong bubblewrap chỉ thấy tệp đăng nhập của chính nó, không thấy thư mục home, repo hay `.env`. Model mặc định nhẹ: `CLAUDE_CODE_MODEL=sonnet`, `CODEX_MODEL=gpt-6-luna` (`CODEX_EFFORT=low`), `ANTIGRAVITY_MODEL=gemini-3.8-flash-medium`. Thử nhanh một backend trên máy: `python3 -I apps/api/app/ai_cli_bridge.py probe codex`. Embedding RAG không qua CLI mà dùng API: Mistral hoặc Gemini (`SEARCH_EMBEDDING_PROVIDER`). Tác vụ nền tiêu quota của gói lập trình; tối đa 2 lượt CLI chạy song song.

## Triển khai cho nhóm nghiên cứu

Chế độ ở trên là cục bộ một người dùng, không đăng nhập. Để cả nhóm dùng chung qua HTTPS với tài khoản
và phân quyền, dùng lớp phủ `docker-compose.team.yml` (ảnh production đóng gói mã, API không mở cổng,
bắt buộc đăng nhập, cookie `__Host-` Secure, lối vào HTTPS bằng Caddy hoặc Cloudflare Tunnel):

```bash
cp .env.team.example .env.team        # điền PUBLIC_URL, POSTGRES_PASSWORD, khóa AI, lối vào HTTPS
make team-backup                      # nếu đang có dữ liệu cục bộ
make team-db-password                 # đổi mật khẩu PostgreSQL cũ khi dùng lại volume cục bộ
make team-up                          # build, khởi động, tự kiểm tra
make team-owner NAME="Họ tên" EMAIL=ban@example.com
```

Sau đó chủ sở hữu thêm thành viên tại **Quản trị → Thành viên** (`/members`); thành viên tự đổi mật
khẩu tại **Tài khoản** (`/account`). Sao lưu định kỳ bằng `make team-backup`. Hướng dẫn đầy đủ, phân
quyền, khôi phục và xử lý sự cố: [`Docs/Team Deployment Runbook.md`](Docs/Team%20Deployment%20Runbook.md).

## Nghiên cứu sâu: câu hỏi → báo cáo có trích dẫn

Trang **Nghiên cứu sâu** (`/research/new`) nhận một câu hỏi và chạy pipeline bốn vai trò trong worker:

1. **Planner** lập 10 truy vấn cho năm góc nhìn: thị trường, use case, đối thủ, kỹ thuật, rủi ro & tuân thủ.
2. **Searcher** tìm qua SearXNG tự host và kho nghiên cứu đã duyệt, tải trang bằng bộ tải an toàn (chống SSRF, ghim IP), cache kết quả tìm kiếm/tải trang có hạn dùng, loại nguồn trùng (URL, mã băm, simhash) và giới hạn số nguồn mỗi tên miền.
3. **Verifier** chỉ giữ nhận định có trích dẫn nguyên văn tìm thấy trong nguồn (khớp chính xác hoặc gần đúng nhưng không được khác phủ định/con số), số liệu trong nhận định phải có trong trích dẫn, rồi kiểm tra suy luận theo lô; thiếu phán quyết thì không dùng.
4. **Writer** chỉ thấy nhận định đã kiểm chứng; máy chủ loại câu không dẫn nhận định hợp lệ, câu có số không có trong bằng chứng hoặc lệch nội dung, xóa link/HTML, rồi gắn trích dẫn `[n](url)` cho từng câu. Báo cáo có câu không nguồn bị từ chối.

Màn theo dõi (`/research/runs/<id>`) hiện sáu bước kèm số đếm theo thời gian thực (Server-Sent Events, tự chuyển sang hỏi định kỳ nếu proxy đệm), báo cáo có số trích dẫn bấm được mở câu gốc trong bảng bằng chứng, chi tiết kiểm chứng (lý do loại từng nhận định), hủy/chạy lại, sao chép liên kết và tải Markdown. Kết quả luôn là bản nháp `deep-research-report` cần chủ sở hữu duyệt. Nút nghiên cứu sâu ở trang **Khoảng trống tri thức** chạy cùng pipeline và gắn báo cáo vào khoảng trống.

Bật tính năng (tắt mặc định):

```bash
# .env
RESEARCH_AGENT_ENABLED=true
SEARXNG_SECRET=$(openssl rand -hex 32)   # ghi giá trị cụ thể vào .env
# RESEARCH_AGENT_PROVIDER=deepseek       # chế độ nhóm tắt cầu nối CLI nên cần nhà cung cấp API

docker compose --profile research-agent up -d searxng
```

SearXNG chỉ nghe trong mạng Docker (không mở cổng). Một số engine (Brave, DuckDuckGo) có thể chặn IP máy chủ; `ops/searxng/settings.yml` bật thêm Bing/Mojeek/Startpage. Giới hạn mỗi người: một lượt đang chạy, `RESEARCH_RUNS_PER_USER_PER_DAY` lượt/ngày, `RATE_LIMIT_RESEARCH_RUNS_PER_WINDOW` lượt/phút và tối đa `RESEARCH_MAX_LLM_CALLS` lượt gọi AI mỗi lượt (kể cả lượt lỗi).

Skill cho Claude Code của nhóm (thư mục `.claude/skills/`):

- `/research-report <câu hỏi>` chạy `scripts/research-report.sh`, lưu báo cáo vào `research-reports/` (gitignore) và tóm tắt kèm trích dẫn. Chế độ nhóm dùng `RESEARCH_API_URL` và token tài khoản dịch vụ có scope `research:run` + `research:read` (token chỉ thấy lượt của chính nó).
- `/research-eval` chạy bộ 8 câu hỏi (`apps/api/app/evaluation/research_eval_v1.json`) cho hai biến thể và so sánh thời gian, lượt gọi AI, token, độ phủ trích dẫn, tỉ lệ trích dẫn khớp nguồn, nguồn trùng, độ phủ góc nhìn:

```bash
docker exec -w /app businessaiagents-api-1 python -m app.operations research-eval --variant naive --output /tmp/naive.json
docker exec -w /app businessaiagents-api-1 python -m app.operations research-eval --variant optimized --output /tmp/optimized.json
docker exec -w /app businessaiagents-api-1 python -m app.operations research-eval-compare /tmp/naive.json /tmp/optimized.json
```

Mỗi lần eval dùng cache riêng nên biến thể sau không hưởng cache của biến thể trước; lượt eval không vào hàng đợi worker.

Chi phí AI đo bằng bảng `ai_call_metrics` (độ trễ, token vào/ra/tổng, token được cache, độ dài prompt cho mỗi lời gọi; không lưu prompt hay câu trả lời):

```bash
docker exec -w /app businessaiagents-api-1 python -m app.operations ai-usage-report --since-hours 24
```

## Chạy để phát triển

API (dùng `apps/api/research.db` nếu chưa đặt `DATABASE_URL`):

```bash
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload
```

Ứng dụng web:

```bash
cd apps/web
npm install
npm run dev
```

Kiểm tra phát triển cổng Discord dùng môi trường khóa riêng:

```bash
cd apps/discord-bot
uv sync --all-extras
```

## Xác minh

```bash
make test
make lint
make build
docker compose config -q
```

Chạy kiểm thử tương tác trình duyệt sau khi bộ dịch vụ Compose đã sẵn sàng:

```bash
cd apps/web
E2E_BASE_URL=http://localhost:3000 npm run test:e2e
```

Điều kiện phát hành và kiểm tra vận hành của Graph Intelligence v2:

```bash
make evaluate-graph-v2
make verify-migrations
docker compose exec -T api python -m app.operations verify-graph
curl --fail http://localhost:8000/api/v1/system/readiness
```

Sao lưu, khôi phục, cờ phát hành, kiểm soát tần suất và xử lý sự cố được mô tả trong `Docs/Graph Intelligence v2 Operations Runbook.md`.

Trình duyệt dùng yêu cầu tương đối `/api/v1`. Next.js chuyển tiếp chúng tới container API nên việc đổi cổng API trên máy không làm hỏng yêu cầu phía khách. Tệp Compose cơ sở chủ động không chuyển `NEXT_PUBLIC_API_URL` từ máy; bản triển khai mở API ở nguồn khác có thể đặt biến này trong cấu hình giao diện riêng.

### Hệ thống thiết kế giao diện

Giao diện có chế độ sáng/tối (theo hệ điều hành hoặc nút trên thanh bên, lưu trong trình duyệt), token màu/chữ/khoảng cách/chuyển động trong `app/globals.css`, viền focus 2px tương phản cao và khung chờ giữ chỗ để trang không nhảy bố cục; vùng đồ thị và bản xem trước tài liệu luôn dùng nền sáng. Ứng dụng dùng mô hình “không gian làm việc nghiên cứu” với nhận diện xanh đại dương: phông Inter Variable tự lưu trữ, nền giấy xanh xám nhạt `#f1f5f3`, nút hành động xanh ngọc dễ tiếp cận `#087a70`, điểm nhấn chàm, bề mặt sáng phẳng và đường viền rõ. Từ `1181px`, sidebar xanh navy chia tuyến thành hai nhóm “Quy trình nghiên cứu” và “Phân tích và tri thức”; vùng nội dung có thanh ngữ cảnh, trạng thái hệ thống và lối tắt tìm kiếm. Máy tính bảng/điện thoại tự chuyển sang thanh trên cùng cùng điều hướng cuộn ngang để mọi không gian vẫn truy cập được. Chân trang tối chỉ giữ tên sản phẩm, ba liên kết chính và bản quyền. Các trang tổng quan, tiếp nhận, tài liệu, nghiên cứu, tìm kiếm, đồ thị, khoảng trống và bộ thu thập dùng chung token, điều khiển biểu mẫu, nhãn, bảng, trạng thái rỗng/lỗi và cách diễn đạt tiếng Việt.

Bộ kiểm thử bao phủ vòng đời và phiên bản nghiên cứu, nhận diện nguồn và chuẩn hóa URL, tìm kiếm chỉ trên dữ liệu đã duyệt, phản hồi đồ thị có kiểm tra/giới hạn, vòng đời Cytoscape, nguồn gốc AI, tiếp nhận RSS sau kiểm duyệt và không gian tài liệu có thể sửa.

Trang `/chat` dùng không gian “Trò chuyện với AI”: lịch sử tìm theo tiêu đề có hoặc không dấu,
hội thoại cuộn độc lập và ô nhập luôn ở cuối vùng làm việc. Trên điện thoại, nút “Lịch sử trò
chuyện” mở/thu gọn danh sách. Ba gợi ý Phát triển ý tưởng, Kết nối kiến thức và Tìm hướng nghiên
cứu chỉ điền câu hỏi để bạn xem lại; Enter gửi, Shift+Enter xuống dòng. Lỗi AI có giải thích
tiếng Việt và mã tra cứu trong “Chi tiết lỗi”. Tạo mới và nhập ChatGPT mở biểu mẫu ngay trong
cột hội thoại; lịch sử gốc, phạm vi, quyền và quy trình duyệt đề xuất được giữ nguyên.

Để dùng khóa riêng, mở **API của tôi** trên `/chat`, chọn OpenAI hoặc DeepSeek, nhập
API key rồi bấm **Tải danh sách mô hình**. Chọn **Mô hình AI** từ danh sách của nhà cung
cấp và bấm **Kiểm tra và kết nối**. Chỉ kết nối khi kiểm tra thành công. Tạo/nhập cuộc trò chuyện
với **Nguồn API → API cá nhân của tôi**. Khóa chỉ ở bộ nhớ trang đang mở và yêu cầu máy
chủ; không lưu localStorage, sessionStorage, database, lịch sử hay log. Tải lại/rời trang,
đăng xuất hoặc đổi tài khoản cần nhập lại; nút **Xóa khóa** chỉ xóa khóa đang giữ tạm.
Mỗi lượt dùng khóa người gửi cung cấp; không tự dùng khóa hệ thống khi thiếu khóa cá nhân.
Mô hình được cố định lúc tạo phiên; nhập lại khóa phải kiểm tra đúng mô hình đó. Tải
danh sách không gọi sinh nội dung; nút kiểm tra gửi một yêu cầu tổng hợp ngắn, tối đa
16 token đầu ra, có thể phát sinh phí và không gửi nội dung nghiên cứu. Lỗi khóa sai,
thiếu credit/hạn mức, quyền hoặc khả năng hỗ trợ mô hình, giới hạn tốc độ và mạng được
giải thích riêng cả lúc kết nối lẫn khi chat. Kết quả thành công chỉ xác nhận tại thời
điểm kiểm tra, không trả số dư hay đảm bảo hạn mức lâu dài. Đổi khóa/model cần kiểm tra
lại; không tự thử nhà cung cấp hoặc model khác. Lịch sử vẫn là kho chung của nhóm.
Chưa hỗ trợ lưu khóa lâu dài, endpoint tùy chỉnh hoặc API cá nhân cho xử lý tài liệu/worker.

Tài liệu LaTeX có thể sửa dùng bản xem trước PDF XeLaTeX thật. Quá trình biên dịch chỉ tồn tại tạm thời và bị giới hạn theo dung lượng nguồn/đầu ra, thời gian và tài nguyên tiến trình; shell escape bị tắt. Ảnh API có các gói TeX Live và phông Noto dùng cho mẫu CV/nghiên cứu độc lập được hỗ trợ. Dự án nhiều tệp và tài nguyên ngoài chưa được hỗ trợ.

Trong phần trò chuyện theo ngữ cảnh tài liệu, lệnh sửa trực tiếp dùng cùng quy trình bản sửa AI gắn với phiên bản như thao tác trên đoạn chọn: hiển thị đầy đủ bản gốc và bản thay thế, chỉ đổi bản nháp cục bộ sau khi người dùng chấp nhận. Câu hỏi và trao đổi ý tưởng chỉ mang tính gợi ý; Tạo/Lưu vẫn là ranh giới ghi dữ liệu bền vững.

## Quy trình xử lý URL

Mỗi URL đi qua cùng vòng đời có giới hạn; bộ điều hợp của từng nguồn chịu trách nhiệm tải và trích xuất:

```text
URL đầu vào
  -> chuẩn hóa và bỏ tham số theo dõi
  -> nhận diện loại nguồn
  -> kiểm tra đích công khai và mọi lần chuyển hướng
  -> tải với giới hạn thời gian, dung lượng và số lần thử lại
  -> trích xuất bằng bộ điều hợp nguồn phù hợp
  -> làm sạch và chuẩn hóa về hợp đồng ResearchDocument
  -> phân loại bằng nhà cung cấp đầu ra có cấu trúc đã cấu hình
  -> lưu để kiểm duyệt
  -> xuất bản vào nghiên cứu/tìm kiếm/đồ thị sau khi duyệt
```

Hợp đồng đã chuẩn hóa gồm URL chuẩn, tiêu đề, tác giả, ngày xuất bản, mô tả, văn bản, nội dung đa phương tiện, siêu dữ liệu, bằng chứng, mức đầy đủ của trích xuất và giới hạn rõ ràng khi chỉ có thể trả kết quả một phần.

| Nguồn | Hành vi đã triển khai | Giới hạn rõ ràng |
|---|---|---|
| GitHub | Siêu dữ liệu kho công khai, README, nhánh/ngôn ngữ chính, cây tệp có giới hạn; URL tệp, issue và pull request | Không clone mất kiểm soát; tài nguyên riêng tư, thiếu hoặc bị giới hạn tần suất trả lỗi có mã; `GITHUB_TOKEN` nâng giới hạn và có thể cấp quyền truy cập |
| Facebook | `facebook.com`, URL di động, bài đăng, Reel, video và chuyển hướng `fb.watch`; siêu dữ liệu Open Graph công khai; bản chép lời có mốc thời gian do người dùng cung cấp và đã kiểm tra | Không vượt đăng nhập, tải media, chống bot hay quyền riêng tư; nếu thiếu bản chép lời, trạng thái vẫn là `partial_success` đến khi nhà nghiên cứu bổ sung bằng chứng và chủ sở hữu duyệt |
| Bài báo khoa học | ID/tóm tắt/siêu dữ liệu PDF arXiv, siêu dữ liệu DOI qua Crossref và phương án CSL trung lập, Semantic Scholar cùng dữ liệu trích dẫn từ IEEE, ACM, Springer, ScienceDirect | Trang có tường phí hoặc chỉ có siêu dữ liệu vẫn là kết quả `partial_success` hữu ích; bản ghi thật sự không tồn tại trả `SOURCE_NOT_FOUND` |
| PDF trực tiếp | Kiểm tra `%PDF`, giới hạn byte/trang, trích xuất lớp văn bản, siêu dữ liệu và bằng chứng; có thể bật Tesseract OCR có giới hạn cho URL và tệp quét | OCR mặc định tắt và bị giới hạn theo trang, điểm ảnh, thời gian, ký tự; trích xuất không có hoặc quá ít nội dung trả kết quả một phần rõ ràng |
| Trang web | URL chuẩn, tiêu đề, mô tả, tác giả/ngày, đề mục, văn bản đã làm sạch và bằng chứng; có thể dùng Browserless sau `JS_RENDER_REQUIRED` | HTTP trực tiếp vẫn là chính; Browserless mặc định tắt, kiểm tra mọi yêu cầu con, chặn media nặng và không vượt đăng nhập/tường phí |

Hệ thống tự theo chuyển hướng và kiểm tra lại mỗi đích để ngăn SSRF. Phản hồi được tải theo luồng và dừng tại `INTAKE_MAX_CONTENT_BYTES` (hoặc `INTAKE_MAX_PDF_BYTES`). Lỗi tạm thời dùng thời gian chờ lũy tiến với số lần hữu hạn; chính sách thử lại tác vụ bền vững là lớp riêng và không bao giờ thử vô hạn.

Trạng thái quy trình gồm `pending`, `processing`, `fetching`, `extracting`, `analyzing`, `completed`, `partial_success` và `failed`. Kiểm duyệt của con người là trạng thái riêng (`needs_review`, `approved`, `rejected` hoặc `duplicate`) để không nhầm tiến độ trích xuất với xuất bản.

Các lỗi nguồn có mã gồm `INVALID_URL`, `SOURCE_NOT_FOUND`, `AUTH_REQUIRED`, `ACCESS_DENIED`,
`RATE_LIMITED`, `FETCH_TIMEOUT`, `CONTENT_TOO_LARGE`, `UNSUPPORTED_CONTENT_TYPE`,
`EXTRACTION_FAILED`, `EMPTY_CONTENT`, `PDF_PARSE_FAILED`, `AI_PROVIDER_AUTH_FAILED`,
`AI_PROVIDER_RATE_LIMITED`, `AI_PROVIDER_UNAVAILABLE`, `AI_RESPONSE_INVALID` và `INTERNAL_ERROR`.
Giao diện không bao giờ hiện stack trace; nhật ký worker giữ ID tác vụ và ngữ cảnh lỗi nội bộ đầy đủ nhưng không chứa bí mật.

### Giới hạn tiếp nhận và cấu hình thử lại

```env
INTAKE_MAX_CONTENT_BYTES=2000000
INTAKE_MAX_PDF_BYTES=25000000
INTAKE_PDF_MAX_PAGES=80
INTAKE_REQUEST_TIMEOUT_SECONDS=20
INTAKE_REQUEST_RETRIES=2
INTAKE_MAX_REDIRECTS=5
INTAKE_MAX_ATTEMPTS=3
INTAKE_RETRY_BASE_SECONDS=30
INTAKE_JOB_LEASE_SECONDS=300
GITHUB_TOKEN=
```

### OCR và dựng trang bằng trình duyệt (tùy chọn)

OCR chỉ chạy khi PDF không có lớp văn bản dùng được. Nó dựng trang trong bộ nhớ, truyền byte PNG tới Tesseract mà không tạo tệp tạm và lưu nguồn gốc theo trang/ngôn ngữ/bộ máy. Chỉ bật cho worker sau khi dựng ảnh API có dữ liệu ngôn ngữ `eng` và `vie`:

```bash
OCR_ENABLED=true docker compose up -d --force-recreate worker
```

Các giới hạn liên quan là `OCR_MAX_PAGES`, `OCR_DPI`, `OCR_MAX_PIXELS`, `OCR_TIMEOUT_SECONDS`, `OCR_MIN_CHARS` và `OCR_MAX_OUTPUT_CHARS`.

Dựng trang bằng trình duyệt là hồ sơ Compose tùy chọn. Cấp cùng token được quản lý cho Browserless và worker; dịch vụ chỉ chạy nội bộ và ảnh được ghim theo digest:

```bash
BROWSER_RENDER_ENABLED=true BROWSERLESS_TOKEN='<managed token>' \
  docker compose --profile browser up -d browserless worker
```

`BROWSER_RENDER_TIMEOUT_SECONDS`, `BROWSER_RENDER_WAIT_MS` và `BROWSER_RENDER_MAX_BYTES` giới hạn từng lượt dựng. Ứng dụng kiểm tra mọi yêu cầu trình duyệt, nhưng môi trường thật cũng nên áp dụng chính sách mạng ra cho container để giảm rủi ro DNS rebinding và bộ máy trình duyệt. Tắt cả hai tính năng khi không vận hành đủ phụ thuộc.

Với Facebook Reel/video công khai, nhà nghiên cứu có thể thêm các dòng mốc thời gian theo thứ tự từ hàng chờ tiếp nhận (`MM:SS văn bản`, `HH:MM:SS văn bản` hoặc số giây). Nội dung đã kiểm tra được lưu làm bằng chứng nguồn, không bị lặp lại trong API hàng chờ hoặc nhật ký kiểm toán; nguồn được xử lý lại từ mã băm đến bước phân loại AI. Vẫn cần chủ sở hữu duyệt trước khi xuất bản.

Màn hình tiếp nhận nhận một hoặc nhiều URL, xem trước loại nguồn, theo dõi tác vụ đang chạy, lọc theo nguồn/trạng thái, hiển thị giới hạn trích xuất và cung cấp thao tác duyệt, từ chối, thử lại cho từng dòng.

## Xác thực và quản lý bí mật

Cổng API và giao diện mặc định chỉ nghe trên `127.0.0.1` (`API_BIND`/`FRONTEND_BIND`); máy khác trong LAN không truy cập trực tiếp được. Runtime cục bộ khuyến nghị bật đăng nhập (`AUTH_MODE=local` trong `.env.example`): tạo chủ sở hữu một lần bằng `make local-owner NAME="Họ tên" EMAIL=ten@example.com` (mật khẩu nhập ẩn, tối thiểu 12 ký tự), rồi tạo lại API/worker. `AUTH_MODE=disabled` (mọi request là chủ sở hữu cục bộ) chỉ dành cho máy phát triển một người và không bao giờ dùng khi mở tunnel hay LAN.

Với bản triển khai dùng chung, hãy bật xác thực cục bộ, tạo chủ sở hữu đầu tiên từ terminal tương tác, rồi tạo lại API và giao diện:

```bash
AUTH_MODE=local
DEPLOYMENT_ENVIRONMENT=staging
AUTH_COOKIE_NAME=__Host-research_session
AUTH_COOKIE_SECURE=true
```

```bash
docker compose exec api python -m app.operations create-user \
  --name "Research owner" --email owner@example.com --role owner --password-stdin
```

Với bản triển khai nhóm, dùng `make team-up`/`make team-owner` theo mục “Triển khai cho nhóm nghiên cứu”; chủ sở hữu quản lý tài khoản ở `/members`, mỗi người tự đổi mật khẩu ở `/account`. Đăng nhập sai liên tiếp bị giới hạn theo từng tài khoản và theo IP; các giới hạn tần suất khác tính theo từng người dùng.

Mật khẩu được băm bằng Argon2. Xác thực trình duyệt dùng phiên mờ có thể thu hồi trong cookie HttpOnly, SameSite và một token CSRF riêng; hệ thống chỉ lưu mã băm token phiên. Các vai trò là `owner`, `researcher`, `viewer`; API thực thi phân quyền bên cạnh việc ẩn điều khiển không phù hợp trên giao diện. Cấu hình staging/production từ chối khởi động nếu tắt xác thực, dùng cookie phiên không an toàn hoặc thiếu tiền tố `__Host-`. Bản triển khai chịu trách nhiệm về HTTPS và bắt buộc dùng khi bật cookie an toàn.

### Tài khoản dịch vụ tiếp nhận trung lập với nguồn

Chủ sở hữu có thể tạo và thu hồi thông tin xác thực của bộ điều hợp qua `/api/v1/auth/service-accounts`. Lúc tạo, hệ thống chỉ trả token bearer `research_svc_...` một lần; chỉ mã băm SHA-256 và tiền tố ngắn để hiển thị được lưu. Chỉ cấp `intake:submit` và/hoặc `intake:read-own`, đồng thời gắn bộ điều hợp với một `source_namespace` ổn định. Token chỉ gọi được các đường dẫn giới hạn theo không gian tên sau:

```text
POST /api/v1/intake/receipts
POST /api/v1/intake/receipts/{receipt_id}/documents
GET  /api/v1/intake/receipts/{receipt_id}
```

Đường dẫn tương thích `POST /api/v1/ingestion/links` vẫn dành cho trình duyệt/người dùng cục bộ và tự tạo biên nhận ngầm. Lưu token bộ điều hợp trong trình quản lý bí mật của bản triển khai, không bao giờ đưa vào mã nguồn hoặc `AI_LOGS`; thu hồi/thay token bằng API chủ sở hữu khi xoay vòng bộ kết nối.

Cấu hình ưu tiên đọc thông tin xác thực từ `/run/secrets/<setting_name>` trước biến môi trường. Dùng `docker-compose.secrets.example.yml` làm lớp phủ sau khi trỏ các biến `*_SECRET_FILE` cần thiết tới tệp riêng tư trên máy. Giữ tệp Compose cơ sở cho phát triển cục bộ; không commit tệp bí mật hoặc ghi giá trị vào `AI_LOGS`.

## Hướng dẫn bảo mật cho nhóm

Đã có trong hệ thống:

- Cổng API/giao diện chỉ nghe `127.0.0.1`; chế độ nhóm bắt buộc đăng nhập, HTTPS qua Caddy/Cloudflare Tunnel, cookie `__Host-` và CSRF. Giới hạn đăng nhập theo tài khoản và IP thật (chỉ tin `X-Forwarded-For` từ mạng Docker, `FORWARDED_ALLOW_IPS`).
- `RequestGuardMiddleware` chặn Host lạ (DNS rebinding) và request thay đổi dữ liệu từ trang khác, kể cả khi tắt đăng nhập. Host thêm (ví dụ `.trycloudflare.com` cho quick tunnel) khai báo ở `API_TRUSTED_HOSTS`.
- Nội dung web/tài liệu chỉ được đưa vào prompt trong khối `<source>` đã làm sạch, sau chỉ dẫn hệ thống chung; nội dung có dấu hiệu prompt injection không được tự duyệt; đầu ra AI có chuỗi giống khóa bị che.
- Mọi route tiêu tốn quota AI có giới hạn tần suất; lời gọi AI có trần token đầu ra.
- Tải nguồn chặn địa chỉ nội bộ và ghim kết nối vào IP đã kiểm (chống SSRF/DNS rebinding); giao diện có Content-Security-Policy.

Quy tắc khi làm việc:

1. Sau khi clone, chạy `scripts/install-git-hooks.sh` để bật hook pre-commit quét secret (gitleaks, phiên bản ghim, kiểm SHA-256). CI (`.github/workflows/security.yml`) quét toàn bộ lịch sử, `npm audit` và `pip-audit`.
2. Không bao giờ đưa khóa vào mã, `.env.example`, AI_LOGS hay ảnh chụp; dùng `.env` (gitignore) hoặc tệp secret (`docker-compose.secrets.example.yml`).
3. Chỉ mở tunnel/LAN khi đã bật đăng nhập (`AUTH_MODE=local`, tạo chủ sở hữu bằng `make local-owner`). Tắt quick tunnel khi không dùng.
4. Token tài khoản dịch vụ cấp scope hẹp nhất (`intake:*` cho bộ thu thập, `research:*` cho skill nghiên cứu) và thu hồi khi không dùng.
5. Duyệt báo cáo AI như duyệt bản nháp của người khác: mở câu gốc trong bảng bằng chứng trước khi xuất bản.

Kiểm tra định kỳ:

```bash
scripts/bin/gitleaks git --redact --config .gitleaks.toml .
(cd apps/web && npm audit)
(cd apps/api && uv export --frozen --no-emit-project --no-hashes -o /tmp/req.txt && uvx pip-audit -r /tmp/req.txt --no-deps --disable-pip)
```

## Kho đối tượng cho tệp đính kèm

Hệ thống tệp cục bộ vẫn là mặc định. Với MinIO hoặc dịch vụ tương thích S3 được quản lý bên ngoài, đặt các giá trị phía máy chủ sau cho cả API và worker:

```env
DOCUMENT_STORAGE_BACKEND=minio
MINIO_ENDPOINT=minio.example.internal:9000
MINIO_ACCESS_KEY=managed-outside-source-control
MINIO_SECRET_KEY=managed-outside-source-control
MINIO_SECURE=true
MINIO_BUCKET=research-documents
MINIO_REGION=
MINIO_AUTO_CREATE_BUCKET=false
```

Bucket production cần được tạo trước khi ứng dụng khởi động; tự tạo bucket chỉ là lựa chọn rõ ràng cho phát triển/tích hợp. Đối tượng từ xa mới nhận tham chiếu mờ `minio://<bucket>/...`. Khóa dạng cũ vẫn đọc từ `DOCUMENT_STORAGE_DIR`, vì vậy phải giữ và sao lưu volume đối tượng cục bộ cho đến khi một đợt migration đã được xác minh riêng và phê duyệt. Đổi backend ghi không di chuyển hoặc xóa đối tượng lịch sử. Thông tin xác thực và khóa đối tượng của không gian tài liệu chỉ ở máy chủ, không bao giờ được API tải lên/tải xuống trả về.

### Di chuyển đối tượng cục bộ cũ

CLI vận hành luôn chạy thử trước và không có chế độ xóa. Bắt đầu bằng bản kiểm kê tổng hợp khi volume cục bộ vẫn đang được gắn:

```bash
docker compose exec -T api python -m app.operations migrate-objects --mode plan
```

Trước khi thực thi cần có `clean=true`. Hãy tạo bản sao lưu khớp nhau cho PostgreSQL và volume cục bộ, tạo sẵn bucket được quản lý, đưa thông tin xác thực MinIO vào dịch vụ API và xin phê duyệt bảo trì rõ ràng. Thực thi yêu cầu cờ chỉ-sao-chép có chủ đích:

```bash
docker compose exec -T api python -m app.operations migrate-objects \
  --mode execute --confirm-copy-only
docker compose exec -T api python -m app.operations migrate-objects --mode verify
```

Mỗi đối tượng được truyền theo luồng tới MinIO, đọc lại và so sánh số byte cùng SHA-256 trước khi commit tham chiếu tệp/không gian. Nguồn cục bộ được kiểm tra lại và giữ nguyên; bản ghi kiểm toán có mã băm và số lượng nhưng không chứa khóa đối tượng thô. Có thể tiếp tục lượt chạy bị gián đoạn; tham chiếu đã di chuyển sẽ được bỏ qua. `verify` kiểm tra các tham chiếu do lệnh migration tạo và yêu cầu bản từ xa khớp nguồn cục bộ được giữ lại. Không xóa volume cục bộ chỉ dựa vào `execute`; dừng dùng volume là thao tác được phê duyệt riêng sau khi xác minh sao lưu và chính sách lưu giữ. Xem `Docs/Graph Intelligence v2 Operations Runbook.md`.

## Dữ liệu giám sát vận hành

Đầu ra chuẩn của API và worker mặc định dùng nhật ký JSON. Phản hồi API trả `X-Request-ID`; bên gọi có thể cung cấp giá trị liên kết gồm chữ, số, `.`, `_`, `:` hoặc `-` (tối đa 128 ký tự); giá trị không an toàn sẽ bị thay. Nhật ký chỉ cho phép các trường định trước và bỏ nội dung body, header tùy ý, URL/chuỗi truy vấn thô, nội dung tài liệu/trò chuyện, phản hồi nhà cung cấp, thông tin xác thực và câu lỗi ngoại lệ. Sự kiện kiểm toán PostgreSQL vẫn là dấu vết nghiệp vụ có thẩm quyền.

Chỉ số Prometheus nằm trong từng tiến trình, đặt lại khi khởi động và mặc định bị tắt. Để trình thu thập bên ngoài đọc chỉ số API, hãy cấp một bí mật riêng khi triển khai:

```env
LOG_FORMAT=json
METRICS_ENABLED=true
METRICS_BEARER_TOKEN=managed-outside-source-control
```

Thu thập `GET /metrics` với `Authorization: Bearer <secret>`. Bật chỉ số mà không có bí mật hợp lệ sẽ đóng an toàn bằng HTTP 503; thiếu hoặc sai xác thực trả HTTP 401. Không dùng lại thông tin xác thực AI, cơ sở dữ liệu hoặc kho đối tượng. Worker phát kết quả tác vụ có cấu trúc nhưng không mở cổng chỉ số thiếu xác thực. Bản triển khai production vẫn chịu trách nhiệm về TLS/chính sách mạng, cấp bí mật cho trình thu thập, thời gian lưu, quy tắc cảnh báo, bảng theo dõi và tổng hợp nhiều bản sao.

## Chế độ bản chiếu tìm kiếm

PostgreSQL vẫn là nguồn chuẩn. Mặc định `SEARCH_DATA_PROVIDER=postgres` và `VECTOR_DATA_PROVIDER=postgres` giữ đường tìm kiếm cục bộ nhẹ. Bản chiếu production tùy chọn dùng hồ sơ Meilisearch chỉ nội bộ cho tìm kiếm từ khóa chịu lỗi gõ và bảng PostgreSQL `vector(1024)` riêng cho tìm kiếm cosine bằng Mistral hoặc Gemini:

```env
SEARCH_DATA_PROVIDER=meilisearch
VECTOR_DATA_PROVIDER=pgvector
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_API_KEY=managed-admin-key
MEILI_MASTER_KEY=managed-server-master-key
SEARCH_EMBEDDING_MODEL=mistral-embed
MISTRAL_API_KEY=managed-provider-key
```

Embedding qua Gemini API (`gemini-embedding-2`, có gói miễn phí, vẫn 1024 chiều nên không cần migration): đặt `SEARCH_EMBEDDING_PROVIDER=gemini`, `SEARCH_EMBEDDING_MODEL=gemini-embedding-2` và `GEMINI_API_KEY` (tạo ở Google AI Studio). Ở gói miễn phí, Google được dùng nội dung gửi lên để cải thiện sản phẩm, kể cả nội dung tài liệu tải lên khi RAG lập chỉ mục. Truy vấn và tài liệu được thêm tiền tố truy hồi theo khuyến nghị của Google; tìm kiếm chỉ so vector cùng nhà cung cấp/model, nên sau khi đổi phải dựng lại pgvector và lập chỉ mục lại RAG tài liệu (trước đó chat theo tài liệu dùng trích đoạn toàn văn).

Khởi động Meilisearch, tạo lại API với các nhà cung cấp đã chọn, rồi để chủ sở hữu dựng lại cả hai bản chiếu. Trong chế độ cục bộ tin cậy, bên gọi không xác thực được coi là chủ sở hữu; bản triển khai có xác thực phải gửi phiên và mã CSRF như bình thường.

```bash
docker compose --profile search up -d meilisearch
docker compose up -d --force-recreate api
curl --fail -X POST http://localhost:8000/api/v1/search/rebuild \
  -H 'Content-Type: application/json' \
  --data '{"projections":["meilisearch","pgvector"]}'
```

Lượt dựng lại tạo và kiểm tra chỉ mục staging hoàn chỉnh trước khi hoán đổi Meilisearch nguyên tử. Nó tạo embedding cho các đoạn tài liệu đã duyệt, có giới hạn, rồi thay hàng pgvector trong giao dịch. Kết quả tìm kiếm chỉ chứa ID đã xếp hạng và được bổ sung từ hàng PostgreSQL hiện tại đã duyệt; nhà cung cấp được chọn sẽ báo lỗi rõ thay vì âm thầm đổi hướng. Volume Meilisearch có thể dựng lại và dịch vụ không mở cổng máy chủ. Ngoài phát triển cục bộ, cấp thông tin xác thực riêng cho máy chủ/API bằng `docker-compose.secrets.example.yml`; bản sao lưu PostgreSQL vẫn là chuẩn.

Để chứng minh bản triển khai, chạy `python -m scripts.verify_search_projections` trong container API đã cấu hình Meilisearch và Mistral. Lệnh kiểm tra dựng lại lặp, dọn hàng cũ có kiểm soát, đọc từ khóa/ngữ nghĩa, đối chiếu số lượng chuẩn, chiều vector và HNSW, đồng thời chỉ in số liệu tổng hợp.

## Chế độ đồ thị

Không gian `/graph` hiển thị đồ thị tri thức nghiên cứu đã duyệt theo hai chế độ phối hợp. Chế độ quan hệ và phân cấp luôn dùng cùng tập nút; phân cấp suy ra nút cha hiển thị theo quy tắc xác định từ các cạnh quan hệ đã duyệt, nên thay đổi quan hệ đã áp dụng xuất hiện ở cả hai. Giới hạn mặc định là 1.000 nút và 4.000 cạnh. Kiến trúc chuẩn Business AI Agents được tách riêng tại `/graph/system` và `GET /api/v1/graph/system`.

Mỗi tệp tải lên đọc được cũng có đồ thị độc lập trong không gian tài liệu, không phụ thuộc điểm định tuyến về mức phù hợp nghiên cứu. “Xem phân tích” mở thẳng đồ thị đó. Phần xem nút hiển thị tóm tắt dựa trên nguồn, tối đa 200 ký tự, nghiên cứu AI độc lập tùy chọn và so sánh rõ giữa tài liệu với AI. AI có thể chuẩn bị bộ thay đổi đồ thị dạng nháp, nhưng xuất bản vẫn phải qua kiểm tra, xem xét, duyệt và áp dụng.

Chọn nhà cung cấp backend bằng:

```env
GRAPH_DATA_PROVIDER=postgres  # bản chiếu PostgreSQL mặc định, có thể dựng lại
GRAPH_DATA_PROVIDER=mock      # nhà cung cấp phát triển rỗng nhưng đúng hợp đồng
GRAPH_DATA_PROVIDER=neo4j     # bản chiếu ngoài tùy chọn, không bao giờ là đường ghi chuẩn
```

`GRAPH_DEFAULT_NODE_LIMIT`, `GRAPH_MAX_NODE_LIMIT`, `GRAPH_MAX_EDGE_LIMIT`, `GRAPH_MAX_DEPTH`, `GRAPH_MAX_NEIGHBORS` và `GRAPH_MAX_PATH_HOPS` giới hạn truy vấn đồ thị. Khi chọn Neo4j, hệ thống không âm thầm đổi hướng hoặc hiện dữ liệu giả. Chủ sở hữu phải dựng lại rõ ràng từ PostgreSQL trước:

```bash
export NEO4J_PASSWORD='<local integration password>'
docker compose --profile neo4j up -d neo4j

GRAPH_DATA_PROVIDER=neo4j NEO4J_URI=neo4j://neo4j:7687 \
  docker compose up -d --force-recreate api
curl --fail -X POST http://localhost:8000/api/v1/graph/rebuild
```

Dịch vụ tùy chọn không mở cổng máy chủ và được ghim vào Neo4j Community 5.26.12 bằng digest ảnh. Lượt dựng lại kiểm tra cả bản chụp quan hệ lẫn phân cấp, dùng ràng buộc duy nhất kết hợp và ghi tham số theo lô, chỉ dọn hàng bản chiếu cũ có nhãn, rồi trả số lượng đối chiếu cho từng chế độ. Ứng dụng mặc định dùng PostgreSQL. Ngoài phát triển cục bộ, cấp `/run/secrets/neo4j_password` cho API và bí mật Docker `neo4j/password` riêng cho máy chủ; kết thúc kết nối Bolt mã hóa theo chính sách mạng/TLS của bản triển khai.

### Trao đổi ý tưởng trên đồ thị có kiểm soát

Không gian `/chat` dùng vòng công cụ có kiểm soát, trung lập với nhà cung cấp để phát triển ý tưởng trong phạm vi đồ thị, tài liệu, nút, trụ cột, khoảng trống hoặc bộ thay đổi có giới hạn. DeepSeek Chat Completions hiện là mặc định; OpenAI Responses vẫn có thể chọn qua `GRAPH_CHAT_DEFAULT_PROVIDER`. Tin nhắn được lưu cục bộ, yêu cầu OpenAI dùng `store=false`; ngữ cảnh gửi lên đám mây được giới hạn và che dữ liệu nhạy cảm.

Nhà nghiên cứu cũng có thể dán liên kết công khai chính thức `https://chatgpt.com/share/<conversation-id>`. Máy chủ nhập một bản chụp có giới hạn mà không dùng thông tin xác thực/cookie đăng nhập của người dùng, rồi tạo nhánh trò chuyện cục bộ độc lập. Tin nhắn nhập và tin nhắn cục bộ có nhãn riêng; các lượt sau không cập nhật hoặc đồng bộ ngược về ChatGPT. Trò chuyện riêng tư, chỉ dẫn ẩn, suy luận, tệp và ảnh tải lên không công khai sẽ không được nhập. Con trỏ ảnh công khai do OpenAI lưu trữ trong bản chụp được kiểm tra, lưu tạm cục bộ, tải lười qua API cùng nguồn mà không gửi referrer và không đi vào lịch sử nhà cung cấp. Văn bản tin nhắn được dựng dưới dạng GitHub-flavored Markdown đã làm sạch, không thực thi HTML nhúng.

Xác minh cấu hình mặc định bằng một lần gọi tối thiểu, không làm lộ bí mật:

```bash
docker compose exec -T api python -m app.operations verify-chat-provider
```

Để gắn bí mật DeepSeek theo phạm vi hẹp, giữ tệp bí mật ngoài kho mã:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
DEEPSEEK_API_KEY_SECRET_FILE=/absolute/private/path/deepseek_api_key \
  docker compose -f docker-compose.yml \
    -f docker-compose.deepseek-secret.example.yml \
    up -d --no-deps --force-recreate api
```

Để chuyển lại sau này, đặt `GRAPH_CHAT_DEFAULT_PROVIDER=openai`, thay bí mật OpenAI được quản lý, tạo lại API và xác minh rõ quyền truy cập dự án/mô hình:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 \
OPENAI_API_KEY_SECRET_FILE=/absolute/private/path/openai_api_key \
  docker compose -f docker-compose.yml \
    -f docker-compose.openai-secret.example.yml \
    up -d --no-deps --force-recreate api
docker compose exec -T api python -m app.operations verify-openai
```

Lệnh chỉ trả các trường trạng thái được phép và kết thúc khác 0 khi có lỗi nhà cung cấp có mã; nó không in thông tin xác thực, câu lệnh, nội dung phản hồi, ID yêu cầu hoặc ID phản hồi.

Trợ lý có thể đọc ngữ cảnh theo phạm vi và tạo đề xuất thay đổi đồ thị, nhưng không thể xuất bản hoặc xóa dữ liệu đồ thị. Mọi nút, cạnh, tên thay thế hoặc bằng chứng đề xuất đều được ghi vào bộ thay đổi nháp và phải qua kiểm tra cùng quy trình con người duyệt/áp dụng. Điều chỉnh giới hạn bằng các biến `CHAT_MAX_*` trong `.env.example`.

## Ghi chú kiến trúc

- Đường dẫn API ổn định dưới `/api/v1`.
- PostgreSQL lưu bản ghi chuẩn, sự kiện outbox và hàng đợi tác vụ tiếp nhận bền vững.
- Tiếp nhận URL trả một nguồn đã xếp hàng; `worker` trong Compose nhận tác vụ bằng lease, thử lại lỗi tạm thời với thời gian chờ lũy tiến và chuyển lỗi hết lượt/vĩnh viễn sang `dead-letter` để người dùng chủ động thử lại.
- Tìm kiếm và đồ thị là các bản chiếu có thể dựng lại. Meilisearch/pgvector và Neo4j là lựa chọn rõ ràng, báo lỗi thấy được; PostgreSQL là nguồn chuẩn duy nhất.
- Mistral là nhà cung cấp mặc định. Hệ thống không có AI giả trong tiến trình: hãy đặt khóa nhà cung cấp thật hoặc chọn `ollama` và cấu hình mô hình cục bộ truy cập được.
- Bộ điều hợp đám mây gồm OpenAI, DeepSeek, Gemini, OpenRouter và Mistral. Có thể cấp khóa API qua tệp `/run/secrets` được quản lý (ưu tiên ngoài phát triển cục bộ) hoặc biến môi trường; với Mistral dùng `MISTRAL_API_KEY` và tùy chọn `MISTRAL_MODEL`.
- Thu thập RSS vẫn chạy đồng bộ khi yêu cầu thủ công và giữ nguồn gốc của nguồn, lượt chạy, đánh giá và tiếp nhận.
- Không gian tài liệu dùng một trình soạn thảo “Nội dung tài liệu” để viết trực tiếp hoặc nhập Markdown/TXT/LaTeX/reStructuredText/AsciiDoc/HTML cục bộ trước khi tạo rõ ràng. Văn bản chưa lưu được giữ tạm theo người dùng trình duyệt để phục hồi khi tải lại; chỉ xóa sau khi tải lên có kiểm soát thành công hoặc người dùng bỏ bản nháp.
- Bảng trao đổi theo ngữ cảnh nằm cạnh nguồn mới và nguồn tải lên có thể sửa. Nút Gửi chỉ truyền ngữ cảnh hiện tại đã giới hạn/che dữ liệu cùng lịch sử cục bộ gần đây; câu trả lời chỉ đổi văn bản qua thao tác Thay đoạn chọn, Chèn tại con trỏ hoặc Nối cuối, sau đó người dùng Tạo/Lưu riêng.
- Nguồn UTF-8 tải lên vẫn sửa được ở chế độ Nguyên bản, Xem trước và Song song. Lưu thủ công, chấp nhận đoạn AI sửa và khôi phục đều tạo phiên bản nguồn bất biến dựa trên đối tượng; đề xuất AI vẫn là bản nháp đến khi được chấp nhận. Mỗi phiên bản đã xử lý tự làm mới các đoạn pgvector theo tài liệu; đoạn nháp không đi vào tìm kiếm toàn cục.
- Chọn văn bản nguồn sẽ mở bảng sửa theo ngữ cảnh. Chọn văn bản trong cuộc trò chuyện sẽ mở lối tắt Hỏi AI, Giải thích, Tóm tắt; các lối tắt chỉ chuẩn bị bản nháp trích dẫn có giới hạn và vẫn yêu cầu Gửi. Bố cục trò chuyện tập trung theo phiên và luồng; phạm vi/nhà cung cấp/trạng thái ở đầu luồng, liên kết duyệt đồ thị nằm trong tin nhắn gốc.
- DOCX và PDF vẫn có thể xem an toàn và làm tham chiếu nhị phân cho AI đọc; chỉnh sửa vòng kín giàu định dạng và giữ nguyên byte được chủ động hoãn.
- Phát hiện khoảng trống biến khái niệm có độ phủ thấp thành không gian kiểm duyệt. Yêu cầu nghiên cứu sâu tạo bản nháp và chưa thể duyệt cho đến khi con người gửi kiểm tra.
- Cổng Discord tùy chọn tự gửi liên kết từ tin nhắn thường trong danh sách cho phép (không cần `/submit`), yêu cầu tự duyệt có kiểm soát cho liên kết đầy đủ và tin cậy cao, rồi báo khoảng trống tri thức liên quan từ biên nhận giới hạn theo không gian tên. Lệnh `/pin` trong cùng kênh chỉ dựa vào quyền `PIN_MESSAGES` của người gọi/ứng dụng; bot không nhận quyền sửa đồ thị hoặc quản lý khoảng trống.
- Quy trình nghiệm thu cục bộ và trực tiếp có thể chạy được ghi tại [`Docs/Discord Bot Test Runbook.md`](Docs/Discord%20Bot%20Test%20Runbook.md).

## Giới hạn hiện tại

SSO production, triển khai Kubernetes/đám mây, trình thu thập đa nguồn, tín hiệu khoảng trống từ xu hướng/tìm kiếm thất bại và bản tin tuần được chủ động hoãn theo kế hoạch. Nội dung Facebook riêng tư/khóa vùng, tự chép lời media Reel và toàn văn có tường phí vẫn không khả dụng. OCR và dựng trang bằng trình duyệt là bộ điều hợp tùy chọn có giới hạn; hệ thống báo giới hạn bằng mã thay vì vượt kiểm soát truy cập hoặc coi trích xuất rỗng là thành công. Nghiên cứu sâu phụ thuộc chất lượng máy tìm kiếm (engine có thể chặn IP máy chủ) và chỉ đọc trang công khai; trích dẫn được kiểm chứng nguyên văn nhưng người duyệt vẫn phải đánh giá độ tin cậy của nguồn.
