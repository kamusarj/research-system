# Current Handoff

## Cân bằng `stage_searching`, đo lại đối chứng 8 câu (`r2`) và phát hành lên `origin` (2026-11-25 15:56)

Intake 39 (`US-OPTIMIZATION-PROGRAM`, Antigravity). Lượt đo đối chứng lại 8 câu (`r2`, Codex
`gpt-6-luna`, `source_sha256=ebe68beb...`, PostgreSQL tách biệt đã xóa) hoàn tất **16/16 lượt,
0 thiếu usage**:
- **Độ phủ góc nhìn 1,000 (5/5) ở TẤT CẢ 16/16 lượt** (8/8 `reference` + 8/8 `optimized`) và độ phủ
  trích dẫn `1,000`.
- **Tổng token: 897.992 → 481.846 (−46,3%)**, prompt −45,7%, lệnh gọi AI 71 → 48 (−32,4%), thời gian
  TB 142,2s → 113,5s (−20,2%), độ phủ thực thể TB tăng **0,400 → 0,450 (+12,5%)**.
- `research-eval-compare` giảm từ 6 xuống còn 2 điểm dao động từng câu (`q6-roi`, `q8-sme-vietnam`
  giảm 1 thực thể dù trung bình cao hơn). Giữ nguyên chuẩn không hạ cổng (`US-OPTIMIZATION-PROGRAM`
  giữ `in_progress`). Artifacts: `docs/evaluations/research-agent/2026-11-25-r2-*`.
- Đã kiểm tra đầy đủ CI cục bộ (API 939, bot 56, web 236 + eslint/tsc/`npm run build`, 3 Compose
  config, `gitleaks` 0 leak), restart `worker`/`api` (health 200, anon 401, `/graph` 200) và đóng
  gói commit theo từng lớp (`14ed9fa`, `d4566f6`, `7e24ba7` + commit docs/AI_LOGS) để đẩy lên
  `origin/feature/research-system-mvp`. Chi tiết: [phiên 1515](SESSIONS/2026-11-25-1515-rank-first-eval-and-release.md).

## Tối ưu lọc đoạn nguyên văn & đo đối chứng đủ 8 câu Research Agent (2026-11-25 14:28)

Intake 38 (`US-OPTIMIZATION-PROGRAM`, Antigravity). Phân tích offline corpus cố định 158 nguồn cho
thấy `dedup` loại 0 nguồn và `llm_cache` lạnh 0 hit nên `optimized` trước đó không giảm được token
so với `reference`. Đã triển khai `select_relevant_passages` (`evidence.py`) và cờ `passage_filter`
(`runner.py`: `True` ở `optimized`, `False` giữ nguyên baseline ở `reference`/`naive`; 5.000 ký
tự/nguồn, tối đa 6 nguồn/lô; đối chiếu trích dẫn và entailment vẫn chạy trên toàn văn gốc), đồng
thời làm rõ `WRITE_TASK` (`research-write-v3-all-perspectives`) cho cả hai biến thể.

`harness-cli story verify US-OPTIMIZATION-PROGRAM` đạt (API **938 passed**, 4 skipped; web **236
passed** / 45 tệp; `ruff` và `git diff --check` sạch). Đo đối chứng đầy đủ **8 câu × 2 biến thể**
trên PostgreSQL tách biệt (đã xóa sạch), Codex `gpt-6-luna`, corpus cố định `research-corpus-20261119.json`,
`stop_on_provider_error=True`, lưu artifact chỉ số/hash tại
`docs/evaluations/research-agent/2026-11-25-{reference.json,optimized.json,comparison.md}`:

- **16/16 lượt hoàn tất, 0 lỗi, 0 thiếu usage**:
  - Tổng token: **790.441 → 380.987 (−51,8%)** (mọi câu giảm từ −29,7% đến −63,4%).
  - Thời gian trung bình: **137,5s → 95,7s (−30,4%)**; lệnh gọi AI: **70 → 40 (−42,9%)**.
  - Chất lượng trung bình: `citation_coverage` 1,0 / 1,0; `quote_verification_rate` 0,905 → 0,908;
    `perspective_coverage` 0,925 → 0,975 (7/8 câu `optimized` đủ 5/5, 0 writer fallback);
    `sources_cited` 8,875 → 9,625; `entity_recall` 0,400 / 0,400.
- **Cổng KPI nghiêm ngặt (`research-eval-compare`)**: vẫn ghi `Chưa đủ điều kiện kết luận KPI`
  (giữ `US-OPTIMIZATION-PROGRAM` ở `in_progress`, không hạ chuẩn) do 6 mục từng câu: 3 câu `reference`
  (`q1`/`q6` thiếu `competitors`, `q5` thiếu `use_case`) và 1 câu `optimized` (`q8` thiếu `competitors`)
  dừng ở 4/5 góc nhìn; `q1`/`q2` giảm 1 thực thể (`0,4 → 0,2`, bù lại `q5`/`q6` tăng).
  Nguyên nhân truy nguyên: `stage_searching` duyệt hết 8 hit của từng truy vấn theo thứ tự nên `market`
  chiếm sớm URL tốt trước các góc nhìn sau.
- Đã kiểm 0 job chạy nền, restart `worker` và `api`: API health 200, ẩn danh `/api/v1/graph` 401,
  Web `:13000/graph` 200. Chi tiết tại [phiên tối ưu](SESSIONS/2026-11-25-1340-research-passage-optimization.md).

## Bàn giao cho Antigravity (2026-11-25)

Đọc [phiên bàn giao](SESSIONS/2026-11-25-1324-antigravity-handoff.md) và [bảng việc](TASKS.md).
Tiếp tục trên workspace hiện tại, nhánh `feature/research-system-mvp`, vì các thay đổi đang làm
vẫn nằm trong working tree. Việc kỹ thuật ưu tiên là kiểm chứng `US-OPTIMIZATION-PROGRAM`.
Mẫu `q1-market-size` sau sửa đã đạt 5/5 góc nhìn và 100% trích dẫn ở cả hai biến thể. Phép đo
KPI giảm 20% token vẫn cần đủ tám câu mỗi biến thể và đầy đủ bằng chứng chất lượng, usage.

Linh còn nghiệm thu Weave/Graph v2 và quyết định commit/push để CI chạy trên GitHub. Các mục
model local, thông tin xác thực, HTTPS nhóm và backup ngoài máy có phụ thuộc riêng trong bản bàn giao.
Lúc bàn giao, API `:18000` và `/graph` trên `:13000` trả HTTP 200. Đĩa trống 9,1 GiB trên `/`
và 5,3 GiB trên `/home`.

## Rút gọn cấu hình mẫu cục bộ (2026-11-25)

Intake 36. `.env.example` giảm từ 245 còn 58 dòng, còn 34 biến. Bỏ các giá trị đã có mặc định,
`DATABASE_URL` do Compose tự ghép, và các tùy chọn vận hành đã có hướng dẫn riêng. Giữ đăng nhập
cục bộ, giới hạn pool, URL cầu nối và chỗ điền cấu hình thiết lập. Compose render khớp trước/sau
ở bốn cấu hình kiểm tra. Xem [phiên dọn cấu hình mẫu](SESSIONS/2026-11-25-1322-trim-env-example.md).

## Sửa độ phủ góc nhìn Research Agent (2026-11-25)

Intake 35, `US-OPTIMIZATION-PROGRAM`. Lượt chẩn đoán `optimized` thiếu nhận định về đối thủ,
đồng thời bản nháp bỏ hai mục đã có nhận định kiểm chứng. Trích xuất giờ ưu tiên góc nhìn của
truy vấn khi nguồn hỗ trợ, còn máy chủ bổ sung mục bỏ sót từ nguyên văn nhận định đã kiểm chứng.
Artifact ghi riêng các góc nhìn có nhận định và thực sự xuất hiện trong báo cáo.
Sau sửa, cả hai biến thể `q1-market-size` đạt **5/5 góc nhìn, 100% độ phủ trích dẫn** và đủ usage.
Comparator chỉ còn chặn do chưa đủ tám câu. Harness verify đạt (API 935, web 236). Database thử
đã xóa, worker local đã nạp mã mới, hai endpoint kiểm tra trả HTTP 200.
Xem [phiên sửa độ phủ góc nhìn](SESSIONS/2026-11-25-1150-research-perspective-coverage.md).

## Kiểm chứng đánh giá đối chứng Research Agent (2026-11-25)

Intake 34, `US-OPTIMIZATION-PROGRAM`. Công cụ so sánh kiểm tra nhãn/cờ của hai biến thể và
checksum của corpus cố định trước khi xác nhận KPI. Cờ `--stop-on-provider-error` ghi chi phí
các câu đã thử và thoát mã `2` nếu gặp lỗi provider. Harness verify đạt, API **933 ca đạt**
(4 bỏ qua) và web **236 ca đạt**.
Preflight Codex `gpt-6-luna` đạt. Hai lượt `q1-market-size` hoàn tất trên PostgreSQL tách biệt,
cùng bộ nguồn. Cả hai có đủ usage, trích dẫn 100% và góc nhìn 80% so với ngưỡng 100%. Công cụ
giữ KPI mở vì thiếu bảy câu và một cổng chất lượng. Database thử đã xóa. Cần kiểm tra phần
thiếu góc nhìn của câu này trước khi đo lại đủ tám câu.
Xem [phiên kiểm chứng](SESSIONS/2026-11-25-1136-paired-eval-guard.md).

## Dọn journal lưu trữ của hệ thống (2026-11-25)

Intake 33 chạy `journalctl --vacuum-size=400M` theo yêu cầu. Dọn 61 tệp journal đã lưu trữ,
thu hồi **807,8 MiB**. Tổng journal còn **398 MiB**, trong đó journal đang ghi là 32 MiB.
Phân vùng `/` còn **9,74 GB** khả dụng. `systemd-journald` active, API và frontend trả 200.
Xem [phiên dọn journal](SESSIONS/2026-11-25-1125-journal-cleanup.md).

## Dọn cache trên `/home` (2026-11-25)

Intake 32 đã dọn hai file cache database Trivy của Deka, thu hồi khoảng **1,63 GB**. `/home`
còn khoảng **5,69 GB** khả dụng. Cache `uv` còn **1,1 GiB** vì một tiến trình `uv` của phiên
Codex giữ khóa và tiến trình Python con nạp thư viện trực tiếp từ cache. Cả `uv cache clean`
và `uv cache prune` đều chờ khóa. Cần dọn khi tiến trình đó kết thúc. API và frontend trả 200.
Xem [phiên dọn cache trên home](SESSIONS/2026-11-25-1123-home-caches.md).

## Dọn image Docker của Deka, Smart Exam và Cineforge (2026-11-25)

Intake 31 gỡ 7 image được xác nhận không có container tham chiếu. Deka gỡ image đánh giá;
Smart Exam gỡ 3 image web/API phát triển và ChromaDB `latest`; Cineforge gỡ hai image build web/API.
Bộ image cấu hình triển khai Deka và các tag rollback vẫn có mặt. Proxy Deka vẫn chạy.

Phân vùng `/` từ **5,31 GB lên 8,90 GB** khả dụng, thêm **3,59 GB**. Danh mục 15 container
và 40 volume khớp trước/sau. API và giao diện dự án hiện tại trả 200.
Chi tiết tại [phiên dọn image](SESSIONS/2026-11-25-1116-docker-project-image-cleanup.md).

## Kiểm kê và dọn phân vùng root (2026-11-25)

Intake 30 đo bằng quyền quản trị: `/var/lib/containerd` 17,57 GB, `/var/lib/docker` 2,26 GB,
giải thích phần lớn chênh lệch 21,18 GB giữa `df` và quét bằng tài khoản thường. Đã dọn cache APT,
10 revision Snap vô hiệu hóa, 17 blob cache Snap độc lập, cache BuildKit và ba image công khai
không có container tham chiếu (Adminer, Gitleaks và cloudflared).

Dung lượng khả dụng trên `/` từ **767 MB lên 5,31 GB**. Đã đối chiếu danh mục volume/container,
kiểm cả image build mới và tag rollback. API và frontend trả 200. Cache BuildKit còn 0 B.
Xem [phiên kiểm kê và dọn đĩa](SESSIONS/2026-11-25-1110-root-disk-cleanup.md).

## Build image API/worker và frontend standalone (2026-11-25)

Intake 29 đã build `businessaiagents-api:local-build-20261125` và
`businessaiagents-frontend:local-build-20261125`. API dùng lại image dependency TeX/OCR có SHA-256
lockfile khớp và `pip check` đạt. Frontend compile trong Node 22 Alpine bằng volume npm đã xác minh,
đóng gói bằng target `runner` của Dockerfile. Bản audit hiện nằm trong hai image local mới.

Container hardening, OCR, LaTeX và migration PostgreSQL đạt. Trong mạng thử tách biệt, API và worker
chạy được, frontend phục vụ hai trang đồ thị và JavaScript, proxy API health trả 200 và đồ thị ẩn danh
trả 401. Stack local đang hoạt động như trước, sẵn sàng cho Linh nghiệm thu. Phân vùng Docker còn khoảng
731 MiB khả dụng sau build. Xem [phiên build](SESSIONS/2026-11-25-1105-local-production-build.md).

## Dọn cache Docker BuildKit toàn máy (2026-11-25)

Intake 28 dọn cache của mọi dự án trên builder local `default` theo yêu cầu của Linh.
BuildKit báo 1,097 GB cache đã dọn và 0 B còn lại. Dung lượng khả dụng đo trên filesystem
tăng từ 435,9 lên 1.199,4 MiB, thêm 763,5 MiB. Đối chiếu danh mục image, container và volume
trước/sau khớp. API health và `/graph` trả 200.
Chi tiết tại [phiên dọn BuildKit](SESSIONS/2026-11-25-1051-docker-build-cache-cleanup.md).

## Dọn Docker và xác minh PostgreSQL, sao lưu (2026-11-25)

Intake 27 đã gỡ hai image build của dự án không còn container tham chiếu, `businessaiagents-ollama-bridge:latest`
và `businessaiagents-discord-bot:latest`. Phân vùng Docker từ 0 lên 437 MiB khả dụng. Tất cả volume
dự án và hai image rollback `pre-hardening-20261103` vẫn có mặt.

PostgreSQL local đã tạo được database thử trên cùng volume. Migration upgrade/check/downgrade/re-upgrade
và 21 ca lease/pgvector đạt. Database thử đã được dọn. Backup service exit 0 lúc 09:46, tạo bản
`20261125-094606-090959`. Kiểm tra verify-only xác nhận manifest, catalogue PostgreSQL và archive
4 tệp. Sau khi backup, API và frontend healthy, worker chạy, UI và API health trả 200.

Dung lượng còn ít cho lần build lớn. Linh có thể nghiệm thu Weave/Graph v2 trên bản local.
Chi tiết tại [phiên dọn Docker](SESSIONS/2026-11-25-0946-docker-cleanup-and-backup.md).

## Audit lại đồ thị Weave và khôi phục frontend (2026-11-25)

Intake 25 đã có trong cây làm việc khi bàn giao. Intake 26 audit lại đợt sửa đó, sửa 11 lỗi
TypeScript trong lớp vẽ cạnh, khôi phục màu nét SVG và đặt nút nối bằng quan hệ phân cấp phụ
bên trong bảng trụ cột đang mở. Kiểm chứng việc giữ nút được chọn khi đổi bố cục, điều hướng
cạnh bằng bàn phím và chuyển từ kéo card sang chụm hai ngón tay trên Chrome mô phỏng.

Bản production local `:13000` đã build và healthy. `/graph`, `/graph/system` và API health
trả 200, truy cập API đồ thị ẩn danh trả 401. Ba truy vấn đồ thị đọc trực tiếp trên PostgreSQL
local đạt. Kiểm tra đạt 925 API (4 bỏ qua ở lần chạy mặc định), 56 Discord bot, 236 Vitest và
55 Playwright (2 lượt desktop-only bỏ qua). Chạy lại 9 ca đồ thị có kiểm tra bàn phím/cảm ứng
đạt. Migration khứ hồi và 21 ca PostgreSQL đạt trong container thử dùng RAM.

Khi audit, phân vùng `/var/lib/docker` báo 0 dung lượng khả dụng. Dọn cache Webpack của frontend
chưa đủ để tạo database thử trên volume local. Intake 27 đã xử lý vấn đề này. Chờ Linh nghiệm thu
Weave/Graph v2 và quyết định commit/push. Xem [phiên audit 25/11](SESSIONS/2026-11-25-0937-weave-reaudit.md).

## Đồ thị Weave — nhãn và kéo thả (2026-11-20)

Intake 24 của `US-WEAVE-GRAPH-CANVAS` đã hoàn tất. Nút **Nhãn** ẩn/hiện tên và loại nút
trong cả ba chế độ, gồm lớp chữ trên sơ đồ hệ thống, và giữ nguyên mức zoom. Nhấp để chọn
nút không ghim tọa độ. Bộ lọc mới được áp dụng sau khi thả để card và dây nối bám theo thao tác.
Sự kiện hủy chạm trả card về vị trí ban đầu.

Bản local `:13000` đã nạp code. Lint, TypeScript, build và 232 Vitest đạt. Playwright đạt 22
ca trên Chrome desktop/tablet/mobile, bỏ qua 2 lượt của ca dành cho desktop. Cảm ứng kiểm tra
bằng Chrome mô phỏng. Chi tiết tại [session 1450](SESSIONS/2026-11-20-1450-weave-interaction-audit.md).

## Weave graph canvas — sửa sau audit (2026-11-20)

Intake 23 của `US-WEAVE-GRAPH-CANVAS`: đã sửa cả 5 lỗi audit. Card tài liệu bị giới hạn trong
canvas và có nút **Sắp xếp lại**. Hủy kéo khôi phục vị trí và giữ lần bấm kế tiếp, kể cả trên
Chrome mobile mô phỏng cảm ứng. Quỹ đạo cập nhật node chưa ghim khi resize, nút **Nhãn** trong
chế độ Mạng tôn trọng trạng thái tắt khi hover, cạnh phân cấp có đầu mũi tên.

Bản local `:13000` đã build lại và health 200. Vitest 232, ESLint, TypeScript, Playwright 19
đạt (2 ca desktop-only bỏ qua), Harness story complete đạt. Session mới nhất:
[1414-weave-audit-fixes](SESSIONS/2026-11-20-1414-weave-audit-fixes.md).

## Weave graph canvas — 2026-11-20 (đã complete)

User yêu cầu thiết kế biểu đồ theo phong cách weave.figma.com với kéo thả mượt; intake22, lane
normal, story `US-WEAVE-GRAPH-CANVAS`. Phạm vi đã chốt với Linh: mọi biểu đồ node (graph, system
map, document graph), kéo thả tự do kiểu Weave + "Sắp xếp lại", dark theo Weave / light giữ giấy.

- Node = Weave card (bo góc, viền mảnh, accent bar, badge mono, nhãn trong card); edge = bezier
  mượt mọi mode; dark canvas #17171b + dot grid + chrome tối; light giữ nguyên "tờ giấy".
- Kéo thả tự do mọi layout: node bám con trỏ 1:1, chỉ repaint node kéo + cạnh liên quan, kéo xong
  giữ vị trí (pin) qua refresh/resize; "Sắp xếp lại" giải phóng. Đã fix card chồng nhau bằng
  collision theo bề rộng card.
- Proof: vitest **232**, eslint/tsc/build sạch; e2e graph-hierarchy/system-graph/viewport-check/
  graph-drag **16 passed** trên 3 viewport (viewport-check giờ mock auth+graph để chạy được với
  AUTH_MODE=local). `harness-cli story complete` = pass. Screenshot light+dark đã xem tay.
- Runtime :13000 đã build lại từ source (frontend restart, healthy). **Chờ Linh nghiệm thu UI**.
- Files chính: `d3-graph-styles.ts`, `d3-graph-renderer.ts`, `document-graph-canvas.tsx`,
  `globals.css`, e2e specs, `docs/stories/weave-graph-canvas.md`. Session:
  `SESSIONS/2026-11-20-1055-weave-graph-canvas.md`.

## Second audit remediation — 2026-11-20 (đã complete)

User yêu cầu "bắt đầu sửa đi" rồi "tiếp tục"; intake21/high-risk `US-SECOND-AUDIT-REMEDIATION`,
decision0057, packet `docs/stories/second-audit-remediation/`. Đã sửa đủ12 phát hiện và đóng:

- Owner gate cho approved document version/restore/AIaccept và relations; canonical evidence mọi
  origin chặn xóa; restore verify-mặc-định/apply riêng, dừng khi lỗi; lease token/fencing + migration
  additive `8e0a2c4d6f79`; duplicate verdict/TTL/CPU bounds/report gaps; hybrid filter; worker
  secrets; limiter cleanup. Regression từng nhóm: 42+17+38+67 ca.
- Full proof `verify_second_audit_remediation.sh` exit 0: API **920 passed**, web 226/44 file,
  bot 56, lint/lock/shell/diff đạt. PostgreSQL smoke DB tách biệt: migration upgrade/check/downgrade/
  re-upgrade sạch, 21 guard/filter test PG đạt, đã drop DB.
- Runtime đã refresh đúng thứ tự fencing (quiesce worker→api 0 run, migrate lúc api khởi động,
  worker sau); health 200, anon 401. Backup timer cài lại có guard `.restore-*`; restore verify-only
  backup mới nhất `mode=verified`. `harness-cli story complete` = pass.
- Session close: `SESSIONS/2026-11-20-0925-second-audit-remediation-close.md` (kèm 0901/0905/0907
  là ba worker nhóm fix). KPI/paired eval và Mistral tier là proof riêng, không thuộc story.

Cập nhật 2026-11-20. Bản trước (local readiness) giữ tại
[archive](ARCHIVE/2026-11-18-before-deployed-local-models-HANDOFF.md). Task board: [TASKS.md](TASKS.md).
Phiên thiết kế Weave ban đầu: [2026-11-20-1055](SESSIONS/2026-11-20-1055-weave-graph-canvas.md).

## Audit remediation — 2026-11-19 (đã proof/complete)

User yêu cầu sửa toàn bộ đề xuất audit và thử Mistral; intake #19, high-risk
`US-AUDIT-REMEDIATION`, decision 0056. Sessions: `SESSIONS/2026-11-19-0912-audit-remediation-and-mistral.md`,
`SESSIONS/2026-11-19-1035-paired-eval-close.md`.

- Đã sửa writer dùng nguyên văn verified claim; usage/eval bao gồm thất bại và manifest/corpus
  cố định; local model che khóa sau decode, deadline kể cả DNS, UI New/Import; backup nhất quán
  với lock chung; lockfile frontend được áp dụng; CI thêm PostgreSQL/lock check và Node22.
- Proof cuối `verify_audit_remediation.sh` exit 0: API **809 passed**, web 226/44 file, bot 56,
  Ruff/ESLint/TypeScript/lock/shell/`git diff --check` đạt. `harness-cli story complete
  US-AUDIT-REMEDIATION` = pass. Playwright local models 6/6; PostgreSQL smoke + backup/restore
  46 bảng đạt như session 0912.
- Paired eval 8 câu reference/optimized (Codex gpt-6-luna, corpus 158 nguồn công khai cố định,
  DB tách biệt đã tự xóa) hoàn tất. Reference 8/8 (870579 token); optimized 5/8 — q6/q7/q8
  `AI_RESPONSE_INVALID`, usage_missing 18 (415823 token). Artifacts chỉ số/hash:
  `docs/evaluations/audit-remediation/2026-11-19-{reference,optimized,comparison}.{json,json,md}`.
- Kết luận quality gates: **KHÔNG ĐẠT** cho KPI giảm20% (comparison fail: q1/q3/q4/q5 hụt
  perspective per-run; q6/q7/q8 chưa hoàn tất + entity recall giảm). Tổng token thô giảm52%
  không dùng kết luận. Không hạ chuẩn bằng chứng.
- api/worker đã restart nạp bản DNS/usage cuối; health 200. npm audit 0. Mistral `/models`200,
  embedding 1024 chiều; Large403 `tier_not_allowed`, Medium/Small429. Không đổi provider mặc định.
- Root còn ~580MiB; giữ ảnh rollback ngoài repo; không tải model/build ảnh lớn.
- CI `.github/workflows/ci.yml` đã kiểm local, **chưa commit/push** (đợi Linh).

## Current Goal

`US-DEPLOYED-LOCAL-MODELS` (intake #17, decision 0055) đã implemented và Harness `story complete` đạt:
Ollama và máy chủ OpenAI-compatible local dùng được cho chat/JSON qua endpoint operator, cùng máy hoặc
máy cá nhân qua SSH/VPN. Bước tiếp theo là operator cài model thật để nghiệm thu, rồi Linh duyệt UI.

## Current Runtime

- UI: http://localhost:13000; API: http://localhost:18000/api/v1. Cổng chỉ bind 127.0.0.1.
- `AUTH_MODE=local`, `RESEARCH_AGENT_ENABLED=true`; owner đã tạo; anonymous dữ liệu 401, mutation thiếu
  CSRF 403. Credential chỉ trong `~/.config/business-ai-agents/owner-login.json` mode 0600 ngoài repo.
- AI tác vụ/chat mặc định Codex `gpt-6-luna`, effort low; embedding vẫn Mistral. Không tự đổi provider.
- Frontend chạy bản build production trong volume `businessaiagents_frontend_next`; command của compose
  multi-user build lại từ source khi container khởi động. Nếu sửa web mà build cache cũ hơn mtime file,
  xoá volume rồi `up -d frontend` để build sạch (đã làm lần này).
- `local-ai` profile: `ollama-bridge` (172.17.0.1:11435, `/api/tags|version|generate|chat`) và
  `local-openai-bridge` (172.17.0.1:11437, `/v1/models`, `/v1/chat/completions`). Cả hai host-network,
  không mở ports, read-only, cap-drop ALL; team dùng image đóng gói, không mount source. Env cấu hình:
  `OLLAMA_BASE_URL/MODEL/API_KEY`, `LOCAL_OPENAI_BASE_URL/API_KEY/MODEL`, `LOCAL_AI_MAX_RESPONSE_BYTES`;
  upstream bridge: `OLLAMA_BRIDGE_UPSTREAM`, `LOCAL_OPENAI_BRIDGE_UPSTREAM` (loopback hoặc đầu tunnel).
- API/worker UID/GID 10001, root/source read-only, cap-drop/no-new-privileges; backup timer 02:30 giữ 14
  bản tại `~/business-ai-agents-backups/scheduled/`; tunnel gate vẫn bật. Không đụng container project khác.
- Đĩa root còn 9,74 GB khả dụng sau intake 33. Đã xác minh ghi PostgreSQL và sao lưu local ở intake 27.

## Completed This Session (đóng paired eval 2026-11-19)

- Xuất artifact optimized từ container api (`/tmp/baa-audit-optimized-20261119.json`, tmpfs) trước
  khi mất; diff reference khớp bản repo. Artifact chỉ số/hash trong `docs/evaluations/audit-remediation/`.
- Chạy `research-eval-compare` trong container api: kết luận chưa đủ điều kiện KPI; ghi bảng chỉ số
  và quality-gate failures vào `2026-11-19-comparison.md` + README eval + validation story.
- Restart api/worker nạp code DNS/usage cuối (source mount read-only); health 200.
- Proof cuối `verify_audit_remediation.sh` exit 0 (API809/web226/bot56 + lint/lock/shell/diff);
  `harness-cli story complete US-AUDIT-REMEDIATION` = pass.
- Cập nhật HANDOFF/TASKS/session log. (Trước đó cùng ngày: toàn bộ sửa audit + Mistral — xem
  `SESSIONS/2026-11-19-0912` và các session 0901/0903/0906.)

## Verification

- Second audit close 2026-11-20: API **920 passed** (`verify_second_audit_remediation.sh` exit 0);
  web 226/44 file; bot 56; PostgreSQL migration smoke + 21 guard test PG đạt; runtime health 200.
- API (trước đó): 818 passed error-taxonomy; `ruff` sạch. Web: vitest 44 file/226 test;
  typecheck + eslint sạch.
- Playwright: `local-chat-models` 6/6 (desktop/tablet/mobile × ollama/local_openai) trên :13000;
  `personal-chat-api` + `chat-api-validation` 6/6 (bằng chứng session 0912).
- Harness: `story complete US-AUDIT-REMEDIATION` pass; `US-DEPLOYED-LOCAL-MODELS` pass trước đó.
- Paired eval: artifacts reference/optimized/comparison đã lưu; KPI gate KHÔNG ĐẠT (ghi nhận).
- Chưa chứng minh: model thật đã cài trả lời end-to-end; endpoint SSH/VPN thật; CI trên GitHub.
  Không tải model.

## Remaining / External Inputs

- Operator cài Ollama hoặc LM Studio model, đặt env, chạy `--profile local-ai`, kiểm tra chat/JSON thật.
- OpenAI preflight `CHAT_API_KEY_INVALID`; Gemini thiếu key; Claude billing; ChatGPT plan chưa có OAuth
  consent/client ID; team HTTPS chưa có tên miền; offsite backup chưa có đích — giữ nguyên như bản trước.
- KPI token toàn pipeline 8 câu vẫn mở (`US-OPTIMIZATION-PROGRAM`).
- Chỉ Linh quyết định product acceptance Graph v2/UI và apply các draft change set.
- Đĩa root chặt; không prune tài nguyên project khác hoặc ảnh rollback `*:pre-hardening-20261103`.

## Next Best Action

1. Theo dõi kết quả GitHub Actions (`ci.yml` và `security.yml`) sau khi đẩy nhánh
   `feature/research-system-mvp`.
2. Linh nghiệm thu UI Weave/Graph v2 trên `http://localhost:13000` và quyết định apply các draft
   change set theo `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`.
3. Chốt hướng xử lý 2 điểm dao động 1 thực thể từng câu (`q6-roi`, `q8-sme-vietnam`) để đóng
   `US-OPTIMIZATION-PROGRAM` (hiện 16/16 lượt đã đạt 5/5 góc nhìn, 100% trích dẫn, −46,3% token và
   `entity_recall` TB tăng `0,400 → 0,450`).
4. Operator cài model local thật (`--profile local-ai`) khi sẵn sàng để nghiệm thu UI local models.

## In Progress — error taxonomy (intake #20, checkpoint 2026-11-19 11:35 — fix xong, eval bị chặn)

Đã sửa phân loại lỗi research pipeline (nguyên nhân q6-q8 optimized bị ghi `AI_RESPONSE_INVALID`):
- `BridgeProtocolError` mới trong `providers/cli_bridge.py` cho phản hồi sai giao kèo của cầu nối
  (body không phải JSON, payload sai hình dạng) — trước đây là `ValueError` bị map nhầm thành lỗi
  output model.
- `runner.py`: `_llm_failure_code` phân loại trung thực theo cả status HTTP (401/403 →
  `AI_PROVIDER_AUTH_FAILED`, 429 → `AI_PROVIDER_RATE_LIMITED`, khác → `AI_PROVIDER_UNAVAILABLE`);
  `_llm_one` và `stage_extracting` chỉ ghi `AI_RESPONSE_INVALID` cho parse/validation thật. Sự kiện
  chẩn đoán `error_types` được commit trước khi raise. `_enrichment_error` map `BridgeProtocolError`
  → `AI_PROVIDER_ERROR`.
- Regression: 9 test mới + assert error_code ở test budget cũ. Full API **818 passed**, ruff sạch.
  Không đổi prompt/variant/quality gates. api/worker đã restart nạp code cuối; health 200.
- **Ngăn cản đo lại paired eval:** Codex CLI bridge trả 429 `CLI_RATE_LIMITED` cho MỌI lời gọi
  (hạn mức subscription đã hết; bridge log `~` user journal 11:13-11:17). Đã thử chạy lại, q1/q2
  reference thất bại `AI_PROVIDER_UNAVAILABLE` (phân loại mới đúng) rồi chủ động dừng, xóa DB tách
  biệt, không tốn quota. Log: `~/.cache/business-ai-agents/audit-runtime/paired-eval-progress-rerun-20261119.log`;
  script chạy lại: `run-paired-eval-rerun.py` cùng thư mục. **Chờ hạn mức Codex reset rồi chạy lại
  trọn bộ 2 variant** (cùng corpus `research-corpus-20261119.json`, cùng fingerprint code mới).

## Locked Direction

Local-first; PostgreSQL source of truth; graph/search là projection; `/api/v1`; deployable code dưới
`apps/`; RSS MVP; AI không tự ghi đè human fields; báo cáo và graph proposals cần human review.
Kế hoạch: `Docs/Research System Implementation Plan.md`. Không tự migration/retire local objects
sang MinIO production, không tự ký product acceptance, không ghi secret/PII vào AI_LOGS.
