# AI Handoff Log

## Current Goal

- Ngày 2026-10-24 chương trình tối ưu toàn diện (Harness intake #13 / high-risk
  `US-OPTIMIZATION-PROGRAM`, story `docs/stories/optimization-program/`). Đã commit từng bước trên
  `feature/research-system-mvp` (snapshot nền `dce73d7` + các commit sau): pre-commit gitleaks
  (`scripts/install-git-hooks.sh`, `.github/workflows/security.yml`); vá `next` 15.5.28, `sharp`,
  `source-map-js`, vitest 4.1.12 (Vite 8/oxc) → npm audit 0; vá `pypdf` 6.21.2, `pillow` 13,
  `urllib3`, `certifi`, `aiohttp`, `multidict`, pytest 9 → pip-audit 0; Dockerfile API cài từ
  `uv.lock` có kiểm hash (ảnh api/worker đã build lại); cổng 13000/18000 chỉ nghe 127.0.0.1;
  `RequestGuardMiddleware` chặn DNS rebinding/CSRF cross-site; bảng `ai_call_metrics` (migration
  `4a6c8e0b2d35`, đã áp dụng sau pg_dump `~/business-ai-agents-backups/*-before-ai-call-metrics`) +
  `python -m app.operations ai-usage-report`; prompt chuẩn `services/prompts.py` (system chung,
  `<source>` đã làm sạch, max_tokens, temperature 0, chặn tự duyệt khi có dấu hiệu injection,
  Discord auto-approve mặc định tắt); chat giảm 16% ký tự mỗi lượt gọi; tài liệu không liên quan
  bỏ lời gọi AI trích xuất ngữ nghĩa. API 484/484, bot 55/55, web vitest 180/180.
  **Chưa xong**: bật `AUTH_MODE=local` cục bộ chờ Linh chạy `make local-owner`; pipeline câu hỏi →
  báo cáo (SearXNG), UI/dark mode, bảo mật Medium còn lại. **Đĩa còn ~0,7 GB** sau khi build lại ảnh
  API (ảnh mới lưu cả nén + giải nén) — cần Linh giải phóng trước khi kéo ảnh SearXNG.
  Session: `AI_LOGS/SESSIONS/2026-10-24-0052-optimization-audit.md`.

- Ngày 2026-10-24 thêm embedding qua Gemini API miễn phí (Harness intake #12 / high-risk
  `US-GEMINI-EMBEDDING-API` / DEC-063 / decision 0050). `SEARCH_EMBEDDING_PROVIDER=gemini` +
  `SEARCH_EMBEDDING_MODEL=gemini-embedding-2` + `GEMINI_API_KEY`: `batchEmbedContents`, 1024
  chiều (không migration), tiền tố truy vấn/tài liệu (`embed_query`/`embed`), tìm kiếm pgvector
  chỉ so hàng cùng provider/model, 429 chờ theo RetryInfo (≤20 giây). Mistral vẫn là mặc định;
  `embedding_client_from_settings()` thay mọi chỗ gọi `MistralEmbeddingClient.from_settings`.
  Kiểm chứng: API 460/460, 13 test mới, Ruff; API/worker đã khởi động lại; Mistral thật qua
  factory 1024 chiều. **Chưa chuyển runtime**: `.env` chưa có `GEMINI_API_KEY` (độ dài 0). Khi có
  khóa: đặt provider/model trong `.env`, `docker restart businessaiagents-api-1
  businessaiagents-worker-1` (restart service user không tạo lại container), gọi thật, rồi lập
  chỉ mục lại RAG cho 3 tài liệu đang có 9 đoạn Mistral. Lưu ý: gói miễn phí cho Google dùng nội
  dung để cải thiện sản phẩm. Session: `AI_LOGS/SESSIONS/2026-10-24-0040-gemini-embedding-api.md`.

- Ngày 2026-10-23 thay API AI bằng quota CLI đăng ký (Harness intake #11 / high-risk
  `US-SUBSCRIPTION-CLI-AI-BRIDGE` / DEC-062 / decision 0049). Cầu nối máy chủ
  `apps/api/app/ai_cli_bridge.py` (user service `business-ai-agents-ai-cli-bridge.service`,
  `172.17.0.1:11436`, Bearer token trong `~/.config/business-ai-agents/`) chạy Claude Code
  (không công cụ), Codex và Antigravity (`agy`, cả hai trong bubblewrap chỉ thấy tệp đăng nhập
  của chính nó). API thêm nhà cung cấp `claude_code`/`codex`/`antigravity` cho tác vụ JSON và chat
  đồ thị (tool call bằng JSON có cấu trúc). Runtime cục bộ đã chuyển `AI_PROVIDER=codex`,
  `GRAPH_CHAT_DEFAULT_PROVIDER=codex` (`gpt-6-luna`, effort low); `.env` cũ sao lưu ở
  `~/business-ai-agents-backups/.env.before-cli-bridge-*`. Embedding vẫn Mistral. Chế độ nhóm
  luôn tắt cầu nối. Kiểm chứng: 46 test mới + API 420/420, ruff, web tsc/eslint/vitest 55;
  probe thật Claude 3,4 giây/Codex 8,1 giây/agy 16–30 giây; sandbox canary; container→bridge
  200/401; Codex thật từ container (phân loại link, trích đồ thị, chat 2 lượt có công cụ).
  Không gửi link thật hay tạo chat trong database. Quick tunnel vẫn chạy.
  Session: `AI_LOGS/SESSIONS/2026-10-23-2025-subscription-cli-ai-bridge.md`.

- Ngày 2026-10-23 mở truy cập từ điện thoại qua Cloudflare quick tunnel (không đổi code). Runtime
  cục bộ đã chạy sẵn (13000/18000, `AUTH_MODE=disabled`) nên đặt cổng mật khẩu trước khi mở ra
  internet: container `businessaiagents-tunnel-gate` (nginx:alpine, basic auth user `linh`,
  `127.0.0.1:13080` → `frontend:3000`, xóa header Authorization trước khi chuyển tiếp, restart
  unless-stopped); cấu hình/htpasswd/mật khẩu ở `~/.config/business-ai-agents-tunnel/` (ngoài repo).
  Tunnel: user unit tạm `business-ai-agents-quick-tunnel.service` (`systemd-run --user`, không tự
  chạy lại sau reboot); URL `*.trycloudflare.com` ngẫu nhiên, xem bằng
  `journalctl --user -u business-ai-agents-quick-tunnel -o cat | grep trycloudflare`. Kiểm chứng
  qua URL công khai: không mật khẩu 401; `/`, `/chat`, `/api/v1/health` 200. Tắt:
  `systemctl --user stop business-ai-agents-quick-tunnel` và `docker rm -f businessaiagents-tunnel-gate`.
  Session: `AI_LOGS/SESSIONS/2026-10-23-1415-cloudflare-quick-tunnel.md`.

- Ngày 2026-10-14 rà soát toàn bộ luồng và chuẩn bị triển khai cho nhóm (Harness intake #10 /
  high-risk `US-TEAM-DEPLOYMENT-READINESS` / DEC-061). Thêm chế độ nhóm `docker-compose.team.yml` +
  `.env.team.example` + `scripts/team.sh` + `make team-*` (production, đăng nhập bắt buộc, API/DB không
  mở cổng, HTTPS qua Caddy hoặc Cloudflare Tunnel, sao lưu/khôi phục), runbook
  `Docs/Team Deployment Runbook.md`, trang `/members` (owner) và `/account` (đổi mật khẩu). Sửa lỗi đã
  xác nhận: đường vòng xuất bản của researcher (bulk-review, ngưỡng RSS, auto_approve, sửa nghiên cứu
  đã duyệt, đảo trạng thái change set), XSS khi xem HTML gốc, SSRF RSS, duyệt link không nguyên tử,
  nguồn nhỏ giọt treo worker, lease nhận lại vô hạn, worker bị kill khi dừng, kết nối DB bị giữ khi
  gọi AI, rate limit dùng chung IP proxy, frontend không xử lý hết phiên/phân trang/lỗi thao tác;
  worker trước đó thiếu 83 biến cấu hình (nay dùng anchor chung). Kiểm chứng: API 401, Discord 55,
  frontend 180 + lint/tsc, migration parity, build ảnh runner, stack nhóm cô lập (đăng nhập, CSRF,
  phân quyền, khóa đăng nhập sai, backup/restore, HTTPS Caddy) đạt rồi đã gỡ sạch. Runtime cục bộ đã
  sao lưu (`~/business-ai-agents-backups/*-before-team-refactor`) rồi cập nhật: 13000/18000 chạy mã
  mới, 82 nghiên cứu, migration head, autostart đã cài lại và đạt kiểm tra. Chưa commit git; chưa tạo
  `.env.team` (chủ sở hữu chọn HTTPS và khóa). Đĩa còn ~2,8 GB, `make team-up` cần ~8 GB trống.
  Session: `AI_LOGS/SESSIONS/2026-10-14-2330-team-deployment-readiness.md`.

- Ngày 2026-10-12 lúc 22:19 UTC+7 đã tạm dừng runtime theo yêu cầu thử giảm RAM:
  cả bốn container `businessaiagents` (frontend/API/worker/database) đang `exited`,
  cổng `13000`/`18000` không còn lắng nghe. Đã stop user service
  `business-ai-agents.service`; service hiện inactive nhưng autostart vẫn enabled.
  RAM dùng (`free -b`) trước 8,021 GiB, sau ổn định 7,193–7,262 GiB;
  lần đo cuối 7,244 GiB, giảm 795,57 MiB. Docker stats trước dừng tổng 758,62 MiB,
  chủ yếu API 543,1 MiB. Giữ nguyên container/image/bốn named volume; toàn bộ container
  project khác vẫn chạy với ID cũ. Worker dừng với exit 137 sau timeout 30 giây;
  frontend/API/PostgreSQL exit 0. Không tự bật lại trong phiên này. Khi chủ sở hữu muốn
  khởi động lại: `systemctl --user start business-ai-agents.service`; autostart cũng sẽ
  chạy ở lần đăng nhập/boot tiếp theo. Session:
  `AI_LOGS/SESSIONS/2026-10-12-2217-stop-project-ram-check.md`.

- Ngày 2026-10-12 đánh giá chuyển sang OpenRouter miễn phí (chưa sửa code). Code đã có
  `OpenRouterProvider` (`app/services/ai.py`, strict json_schema) cho phân loại link, xử lý
  tài liệu, sửa/nghiên cứu tài liệu qua `AI_PROVIDER=openrouter`. Chưa hỗ trợ OpenRouter:
  graph chat (`graph_chat_default_provider` chỉ openai/deepseek), API cá nhân, embedding
  (`search_embedding_provider` chỉ mistral, cột `PortableVector(1024)`). Giới hạn free
  chính thức: 20 req/phút, 50 req/ngày (1000/ngày nếu đã mua ≥10 credit). API công khai
  ngày 2026-10-12: 19 model giá 0, model có cả tools + structured outputs gồm
  `nvidia/nemotron-3-super-120b-a12b:free`, `openrouter/free`, `apodex/apodex-1.1-mini:free`,
  `dots-studio/dots-3-note-preview:free`, `liquid/lfm-2.5-2.6b:free`; 3 embedding free.
  Rủi ro: giới hạn ngày, model free thay đổi, endpoint free có thể train/giữ prompt. Chờ
  chủ sở hữu chọn phạm vi. Session: `AI_LOGS/SESSIONS/2026-10-12-0945-openrouter-free-assessment.md`.

- Ngày 2026-10-12 kiểm tra read-only RAG. Code có RAG phạm vi tài liệu: worker
  `refresh_document_rag` chia đoạn 4000 ký tự, embed `mistral-embed` 1024 chiều, lưu
  `search_vector_projections` (pgvector); chat phạm vi `document` lấy top-6 đoạn × 1500 ký
  tự theo tin nhắn mới nhất (`graph_chat._document_scope_passages`). Thực tế runtime: hai
  workspace hiện có `rag_status=pending`, 0 chunk → chat tài liệu đang fallback 8000 ký tự
  đầu; `VECTOR_DATA_PROVIDER=postgres` nên `/search/semantic` là LIKE, `/search/hybrid` tắt.
  Bảng vector còn 9 chunk cũ (07/2026) của 3/79 research approved. Hai lần index thành công
  2026-08-07 thuộc workspace đã xóa. Không rebuild (tốn call Mistral thật). Session:
  `AI_LOGS/SESSIONS/2026-10-12-0930-rag-check.md`.

- Ngày 2026-10-12 khảo sát read-only luồng hoạt động chính. Runtime: trình duyệt →
  Next.js `13000` (rewrite `/api/v1/*` → `api:8000`) → FastAPI 4 workers → PostgreSQL;
  `worker` poll hàng đợi DB (link intake + document processing). Luồng: (1) URL →
  `link_submissions` → worker fetch/adapter/AI phân loại (Mistral) → `needs_review` →
  duyệt tạo `research_items` approved + change set nháp + `detect_gaps`; (2) tải tài liệu →
  worker trích xuất/paper-fit/đồ thị tài liệu/RAG → `needs_review`; (3) change set
  draft → validate → review → approve → apply vào đồ thị chuẩn; (4) `/chat` DeepSeek chỉ
  tạo change set nháp. `AUTH_MODE=disabled`; search/graph/vector đều PostgreSQL.
  Quan sát: `outbox_events` 249 dòng, 0 processed, không có consumer trong code. Hàng chờ
  chủ sở hữu: 7 change set link `draft`, 1 link + 1 chat `needs_review`, 2 chat `draft`.
  Không đổi code/container. Session:
  `AI_LOGS/SESSIONS/2026-10-12-0915-main-flow-survey.md`.

- Ngày 2026-10-12 kiểm tra read-only: frontend đúng là chạy bằng Docker ở cổng `13000`.
  Container `businessaiagents-frontend-1` (image `businessaiagents-frontend`, build từ
  `apps/web/Dockerfile` ngày 2026-09-04) publish `0.0.0.0:13000->3000`, healthy, restart
  `unless-stopped`, do systemd user `business-ai-agents.service` (enabled/active) chạy
  `scripts/start_local_autostart.sh` với `FRONTEND_PORT=13000` và override
  `docker-compose.multi-user.yml`. Source bind-mount `apps/web` → `/app`; mỗi lần start
  container chạy `npm run build` rồi `node .next/standalone/server.js` (production), nên
  đổi code cần restart container, không cần rebuild image. Chạy `docker compose up` không
  có `FRONTEND_PORT` sẽ về cổng mặc định `3000`. `/`, `/chat`, `/api/v1/health` qua
  `13000` trả 200. Không đổi code/container. Session:
  `AI_LOGS/SESSIONS/2026-10-12-0900-frontend-docker-port-check.md`.

- Ngày 2026-09-05 hoàn thiện chọn/kiểm tra model cho API cá nhân (intake #9 / high-risk
  `US-CHAT-API-VALIDATION` / DEC-060). UI tải danh mục bằng key, chọn model và chỉ giữ kết
  nối sau probe chủ động thành công. Phân biệt xác thực, quyền/model, credit, spend/usage/
  quota, tốc độ và mạng; chat thực tế dùng cùng classifier. Probe tối đa 16 output token,
  timeout 20 giây, thông báo có thể có phí, không gửi nghiên cứu hay thực thi tool.
  Chặn stale results khi đổi key/provider/model/đóng trang; nhập lại key kiểm tra model
  cố định của phiên cũ. POST models/verify được auth/CSRF/rate-limit; không lưu key.
  Ruff, 380/380 API, 171/171 frontend, ESLint/TypeScript, build 15 route và 15/15
  Playwright production desktop/tablet/mobile đạt. Chỉ restart API/frontend;
  `18000/api/v1/health` và `13000/chat` trả 200, migration head vẫn `3e5f7a9b1c24`,
  dữ liệu vẫn 10 sessions/32 messages. Không gọi AI bằng khóa thật. Probe không trả số
  dư chính xác và chỉ xác nhận tại thời điểm kiểm tra. Session:
  `AI_LOGS/SESSIONS/2026-09-05-1521-chat-api-model-validation.md`.

- Ngày 2026-09-05 thêm “API của tôi” cho `/chat` (intake #8 / high-risk
  `US-PERSONAL-CHAT-API` / DEC-059). Người dùng nhập API key OpenAI/DeepSeek và model riêng;
  khóa chỉ nằm trong bộ nhớ trang/request server, được hủy khi đổi tài khoản/rời trang,
  không lưu browser storage/database/log. Create/import lưu `credential_source`; personal
  send phải có key người gửi, không fallback. Migration additive `3e5f7a9b1c24` đã áp dụng;
  10 sessions/32 messages cũ được giữ nguyên. Đã khớp tên hai PaperEvaluation constraints
  ORM với migration cũ để PostgreSQL Alembic 1.19 check sạch, không đổi điều kiện.
  Ruff + 334/334 API, 14/14 frontend unit, TypeScript/ESLint, build 15 route, SQLite parity
  và 12/12 responsive Playwright đạt. API/frontend đã restart tại `18000`/`13000`;
  không đổi dependency/image hay restart worker/database/Smart Exam.
  Khóa tạm phải nhập lại khi tải lại; lịch sử chat vẫn shared theo hợp đồng nhóm.
  Không gọi AI có phí bằng key thật. Session:
  `AI_LOGS/SESSIONS/2026-09-05-1446-personal-chat-api.md`.

- Ngày 2026-09-05 thiết kế lại nội dung và UI `/chat` theo ảnh chủ dự án cung cấp
  (Harness intake #7 / normal story `US-AI-CHAT-REDESIGN`). Header gọn, lịch sử có tìm kiếm
  không dấu và ngày/trạng thái, biểu mẫu tạo/nhập rộng trong cột hội thoại, ba gợi ý nghiên cứu,
  hội thoại dễ đọc và ô nhập nằm trong viewport. Mobile mở/thu lịch sử; Enter gửi,
  Shift+Enter xuống dòng và bảo vệ IME. Lỗi AI lịch sử được trình bày bằng tiếng Việt,
  mã lỗi trong chi tiết và lối sang chọn AI mới; không thay đổi nội dung lưu trong database.
  ESLint, TypeScript, 11/11 unit, production build 15 route và Playwright 9/9 ba viewport đạt.
  Đã restart riêng frontend, dùng source bind mount để build production; bản mới tại `13000/chat`.
  API/worker/database và bốn Smart Exam container giữ nguyên ID. Nhà cung cấp OpenAI của
  hội thoại lỗi cũ vẫn chưa cấu hình; UI không sửa credential hay tự gọi AI thật.
  Session: `AI_LOGS/SESSIONS/2026-09-05-1414-ai-chat-redesign.md`.

- Ngày 2026-09-04 đã thiết kế lại toàn bộ frontend theo mô hình “research workspace” (Desktop
  Harness intake #6 / normal story `US-RESEARCH-WORKSPACE-UI-REDESIGN` / DEC-058). Desktop dùng
  sidebar xanh đậm chia nhóm quy trình và công cụ tri thức, vùng nội dung có thanh ngữ cảnh; tablet
  và mobile chuyển sang điều hướng ngang. Token màu, button, form, card, table, page header và
  dashboard được làm phẳng, dễ đọc hơn nhưng vẫn giữ nhận diện xanh đại dương, tiếng Việt và toàn bộ
  API/URL/quyền/hành vi hiện có. ESLint, TypeScript, 33 tệp / 146 Vitest, build 15 route, bộ
  Playwright đại diện trên ba viewport, kiểm tra ảnh trực quan và 6 smoke test từ runtime Docker đều
  đạt. Chỉ image/container frontend được build/recreate; API, worker, database/volume và bốn
  container Smart Exam được giữ nguyên. Frontend healthy tại `13000`, API auth tại `18000` trả 200;
  còn 9,4 GB trống trên ổ hệ thống. Harness completion, decision verification, standard trace #6
  và audit entropy `0/100` đạt. Session:
  `AI_LOGS/SESSIONS/2026-09-04-1655-research-workspace-ui-redesign.md`.

- Ngày 2026-09-04 đã build lại và tạo lại runtime Docker tiếng Việt (Desktop Harness intake #5 /
  normal story `US-REBUILD-VIETNAMESE-DOCKER-RUNTIME`). Image API, worker và frontend được build
  tuần tự từ cây mã hiện tại; ba container ứng dụng được recreate bằng cấu hình multi-user trên API
  `18000` / frontend `13000`, còn database container và volume PostgreSQL được giữ nguyên. API trực
  tiếp/qua proxy, frontend và 11 route chính trả HTTP 200; HTML runtime có `lang="vi"` và thương hiệu
  tiếng Việt; readiness là `ready`; migration ở `2d4e6f8a0b13 (head)`; đồ thị hợp lệ với 45 nút / 32
  cạnh; log mới sạch; autostart và cấu hình bốn API worker đạt. ID hai container Smart Exam không
  đổi. Ổ hệ thống ban đầu chỉ còn 1,6 GB; chỉ build cache không còn dùng được dọn, không xóa image
  đang chạy hay volume, và dung lượng trống cuối là 11 GB. Lượt build đồng thời đầu tiên hết chỗ khi
  Docker giải nén hai image API/worker; runtime cũ không gián đoạn và lượt build tuần tự sau đó đạt.
  Harness completion và detailed trace #5 đạt. Session:
  `AI_LOGS/SESSIONS/2026-09-04-1221-rebuild-vietnamese-docker-runtime.md`.

- Ngày 2026-09-04 đã hoàn tất trải nghiệm sản phẩm chỉ dùng tiếng Việt (Desktop Harness intake #4 /
  normal story `US-FULL-VIETNAMESE-EXPERIENCE` / DEC-057). Web được cố định ở tiếng Việt và không
  còn bộ chuyển EN/VI; điều hướng, nội dung trợ năng, các luồng nghiên cứu/tài liệu/đồ thị/chat/nhập
  liệu, phản hồi an toàn của API, hướng dẫn Discord và README/đặc tả/kế hoạch cốt lõi đều dùng tiếng
  Việt tự nhiên, phù hợp nghiên cứu. Định danh kỹ thuật, hợp đồng API/JSON, mã lỗi, tên sản phẩm và
  nội dung nghiên cứu/nguồn gốc được giữ nguyên. ESLint, TypeScript, 145 kiểm thử frontend, bản dựng
  Next.js 15 route, Ruff + 323 kiểm thử API, Ruff + 55 kiểm thử Discord, 45 ca Playwright responsive,
  kiểm tra tĩnh chuỗi hiển thị, hàng rào Markdown và `git diff --check` đều đạt. Harness completion
  và detailed trace #4 đạt. Log lịch sử, migration và dữ liệu nguồn không bị dịch hồi tố để bảo toàn
  nguồn gốc. Chưa rebuild Docker; chỉ nên rebuild sau khi kiểm tra dung lượng đĩa. Session:
  `AI_LOGS/SESSIONS/2026-09-04-1156-full-vietnamese-experience.md`.

- On 2026-08-24 completed a full-project defect and dependency sweep (Desktop Harness intakes #2
  and #3; stories `US-FULL-PROJECT-DEFECT-SWEEP-2026-08-24` and
  `US-FRONTEND-DEPENDENCY-SECURITY-2026-08-24`). Restored separate API/Discord/frontend development
  environments; fixed Makefile Discord commands, container-safe non-incremental TypeScript checks,
  deterministic frontend Docker installs, stale production dependency-volume synchronization and a
  tablet modal E2E interaction. Next.js remains on patched 15.5 Maintenance LTS at 15.5.23 with
  zero full/production npm vulnerabilities. API Ruff + 323 tests, Discord Ruff + 55 tests, frontend
  ESLint/TypeScript + 145 tests + 15-route build, migration parity/live head, 45-node/32-edge graph
  invariants, Compose/autostart, eleven live routes and Playwright 69 enabled desktop/tablet/mobile
  cases pass; six auth-only cases are expected skips. The rebuilt frontend is healthy on `13000`
  and API on `18000`; PostgreSQL/named volumes were preserved and Smart Exam remains healthy on
  `8080`. The scoped frontend recreation initially left all Smart Exam IDs unchanged; its frontend
  and backend were independently recreated later while no sweep command targeted that project.
  A full API image rebuild was stopped before completion because its uncached TeX/OCR
  layer left only about 2 GB on the 96%-full root filesystem; the unchanged live API image and all
  API code/runtime checks pass, and no Docker data was pruned. Harness story completion passes;
  detailed security trace #2 and standard sweep trace #3 meet their required tiers; audit entropy is
  0/100. Re-audit after the separately announced 2026-08-26 Next.js security release. Session:
  `AI_LOGS/SESSIONS/2026-08-24-2352-full-project-defect-sweep.md`.
- On 2026-08-24 repaired local autostart after the repository was moved toward Desktop. The move
  had stopped midway, leaving 137 application files on Desktop and 193 required application files
  on `Data1`; those files plus 842 missing repository/support files (including Git metadata) were
  copied into Desktop without overwriting existing content. The launcher now
  defaults to `$HOME/Desktop/Business AI Agents`, pins Compose identity to `businessaiagents`, and
  no longer tries to mount the retired `/run/media/linh/Data` path. The installed user service is
  enabled/active; all four services are healthy/running on frontend `13000` and API `18000`; every
  application bind source resolves to Desktop; health/readiness, migration head, graph invariants,
  three frontend routes, idempotent restart and restart policies pass. PostgreSQL and all named
  volumes were preserved, and Smart Exam `8080` remained running with unchanged container IDs.
  Desktop Harness completion passes; detailed trace #1 meets 3/3 and audit entropy is 0/100. A real
  cold reboot was not performed. Session:
  `AI_LOGS/SESSIONS/2026-08-24-2319-desktop-autostart-repair.md`.
- On 2026-08-16 restored the existing four-service local stack after the NTFS volume mounted at
  `/run/media/linh/Data1` while the enabled autostart launcher still targeted `/run/media/linh/Data`.
  The stale bind mounts exposed empty `apps/api` and `apps/web` directories, causing API, worker and
  frontend restart loops. The failing user service was stopped and only API, worker and frontend
  were recreated from the real `Data1` repository; PostgreSQL and persisted volumes were preserved.
  All four services are now healthy/running on frontend `13000` and API `18000`; health/readiness,
  migration head, graph invariants, `/`, `/graph`, `/graph/system`, fresh-log scan and bind-source
  checks pass. Its fixed-path autostart follow-up was completed on 2026-08-24. Session:
  `AI_LOGS/SESSIONS/2026-08-16-1514-restore-local-project.md`.
- On 2026-08-14 intake #79 / normal story `US-SYSTEM-MAP-FOREGROUND-LABELS` / owner correction
  intervention #28 applied the same foreground-text protection to `/graph/system`. Every visible
  root, pillar and expanded child label is mirrored into the SVG `.d3-labels` group after all card
  shapes, with a restrained 2.5px canvas-colored outline and no pointer events; source card text is
  visually hidden while each interactive card retains its accessible name. The live projection
  proves 12/12 overlays collapsed and 45/45 expanded, zero horizontal overflow and zero browser
  errors without changing compound containment, folding, selection or data. Full ESLint, 32 Vitest
  files / 144 tests, TypeScript, production build, responsive Playwright 3/3 and Harness completion
  pass. Standard trace #81 records the proof. The rebuilt frontend is healthy on `13000`; API
  remains healthy on `18000`. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1524-system-map-foreground-labels.md`.
- On 2026-08-14 intake #78 / normal story `US-KNOWLEDGE-GRAPH-COMMUNITY-LABEL-LAYER` / owner
  correction intervention #27 fixed Network community headings that the supplied live screenshot
  showed behind node glyphs. Halo circles remain in the background community group, while the 10
  real type/count headings now render in the foreground `.d3-labels` group with a subtle 3px canvas
  outline and no pointer events. Live 429-node Chrome found five actual label/glyph intersections
  (`Research Item · 79` and `Technology · 70`) and proves the text now paints above them, with zero
  overflow or browser errors. Full ESLint, 32 Vitest files / 144 tests, TypeScript, production build,
  responsive Playwright 3/3 and Harness completion pass. Standard trace #80 records the proof. The
  rebuilt frontend is healthy on `13000`; API remains healthy on `18000`. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1134-knowledge-graph-community-label-layer.md`.
- On 2026-08-14 intake #77 applied the owner's text-only cleanup to primary `/graph`. The page
  keeps its title, controls, node labels, compact metrics, error/empty/loading states and safety
  warnings, while removing the redundant eyebrow/intro copy, two hierarchy prose banners, canvas
  guide card and persistent interaction sentence. Hidden-leaf and unplaced counts now share the
  compact bottom status line. Live Chrome at 1920×1080 confirms zero guide cards, zero structure
  banners, `97.0%` studio width, zero horizontal overflow and zero browser errors. Full ESLint,
  32 Vitest files / 144 tests, TypeScript, production build and responsive Playwright 3/3 pass.
  The rebuilt frontend is healthy on `13000`; API health remains available on `18000`. Standard
  trace #79 records the work and proof. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1122-knowledge-graph-text-cleanup.md`.
- On 2026-08-14 intake #76 / normal story `US-KNOWLEDGE-GRAPH-FULL-VIEWPORT` / owner correction
  intervention #26 used the supplied 1920×1080 screenshot to fix the remaining route-level width
  constraint. Only primary `/graph` now opts out of the shared 1440px reading cap and uses responsive
  viewport gutters; Graph changes and every other route retain their current width. The live studio
  increased from the screenshot's approximate 1224px/63.8% to 1862.4px/97.0%; canvas is
  1860.4×864px at 107% readable zoom, with zero horizontal overflow or browser errors. Full ESLint,
  32 Vitest files / 144 tests, TypeScript, production build and responsive Playwright 3/3 pass.
  Runtime is rebuilt/healthy on frontend `13000`; API remains ready on `18000`. Harness story
  completion and standard trace #78 are recorded. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1048-knowledge-graph-full-viewport.md`.
- On 2026-08-14 intake #75 / normal story `US-KNOWLEDGE-GRAPH-CONCURRENT-LOAD` moved the live
  Knowledge Graph runtime from single-process development serving to an autostarted four-worker API
  plus standalone production Next.js mode. Initial Hierarchy no longer performs the redundant
  `/graph/stats` full projection; graph/neighbor reads use bounded per-browser dedupe/cache; large
  JSON is private-cacheable and gzip shrinks the real response from 297,275 to 28,443 bytes; and
  PostgreSQL pools are explicit at 4 + 2 overflow per worker. At concurrency 20, 60/60 proxied gzip
  reads pass at 130.13 ms average versus the 457.53 ms single-process baseline. API Ruff + 323 tests,
  frontend lint/typecheck + 143 tests + build, responsive Playwright 3/3, Compose/autostart and
  readiness pass; Harness completion and standard trace #77 are recorded. Startup now waits for
  API/frontend health; an idempotent second service restart
  preserved every Business AI Agents and Smart Exam container ID. Shared/external deployment still
  requires auth/TLS and a gateway/shared rate limiter. Session:
  `AI_LOGS/SESSIONS/2026-08-14-0956-knowledge-graph-concurrent-load.md`.
- On 2026-08-14 intake #74 / normal story `US-KNOWLEDGE-GRAPH-FIT-SMOOTH` made the explicit
  Knowledge Graph `Fit view` an honest whole-canvas overview and removed the remaining hierarchy
  pointer-time full-SVG work. The expanded real 91-node hierarchy improved from 63–64 cards outside
  the canvas to zero on desktop/tablet/mobile; the zoom badge now matches the actual `13%`/`14%`
  transform; resize work is frame-coalesced; and hierarchy hover updates only the pointed card plus
  indexed incident edges with zero D3 transitions. Full ESLint, 31 Vitest files / 141 tests and
  responsive Playwright 3/3 pass; Harness completion and standard trace #76 are recorded. The
  previously missing `DocumentWorkspace.summary` test fixture was repaired by the follow-up
  concurrent-runtime story, so full TypeScript/build now pass. Runtime remains live on API `18000`
  / frontend `13000`. Session:
  `AI_LOGS/SESSIONS/2026-08-14-0937-knowledge-graph-fit-smoothness.md`.
- On 2026-08-14 intake #73 / normal story `US-LOCAL-RUNTIME-AUTOSTART` configured the local
  Research System to restore automatically after the owner's desktop session starts. Database,
  API, worker and frontend now use Docker `restart: unless-stopped`, matching the Smart Exam
  deployment pattern, while a mount-aware systemd user service handles the repository's NTFS
  `/run/media` ordering and starts only the four core services with `--no-build`. The installed
  service is enabled/active; the runtime is healthy on API `18000` / frontend `13000`; readiness is
  valid at 45 nodes / 32 edges; and an idempotent service restart preserved all Business AI Agents
  and Smart Exam container IDs. A real cold reboot was not performed. Session:
  `AI_LOGS/SESSIONS/2026-08-14-0917-local-runtime-autostart.md`.
- On 2026-08-11 intake #72 / high-risk story `US-DOCUMENT-LIBRARY-SIMPLIFY-DELETE` / DEC-055
  simplified Uploaded documents to `Document · Summary · Size · Actions`. The API now returns a
  bounded normalized summary (research summary, then extracted-content fallback); Edit reuses the
  existing workspace; and confirmed Delete is owner-only. Deletion refuses active processing,
  intake-receipt lineage, or applied document graph provenance, while a permitted delete cleans up
  document/research dependents and stored versions and retains a content-free audit event. Harness
  completion reran Ruff, 38 API tests, 10 frontend tests, ESLint, the 15-route production build and
  desktop/tablet/mobile Playwright 3/3. The bind-mounted runtime already serves the new summary at
  API `18000` and `/documents` at frontend `13000`; no container rebuild was necessary. Detailed
  trace #74 records proof. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1710-document-library-summary-safe-delete.md`.
- On 2026-08-11 intake #71 / high-risk story `US-DOCUMENT-DRAFT-AUTOSAVE-ONLY` / DEC-054 removed
  the Document Workspace `Discard local draft` action and its EN/VI copy. Direct authoring still
  writes every title/format/content change synchronously to the existing bounded per-user
  `localStorage` record, restores after refresh/browser restart, retains work after creation failure,
  and now clears only after successful governed creation. No storage key, API, schema, auth or
  publication contract changed. Focused frontend 24/24, full frontend 138/138, ESLint, TypeScript,
  the 15-route production build and desktop/tablet/mobile Playwright 3/3 pass. The rebuilt runtime
  is live on frontend `13000` / API `18000`; health/readiness and clean log checks pass. Detailed
  Harness trace #72 records the proof. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1548-document-draft-autosave-only.md`.
- On 2026-08-11 confirmed and kept the existing four-service local stack running without rebuilding
  images or changing application code/data. The conflict-free ports remain frontend `13000`, API
  `18000`, with PostgreSQL healthy and worker running. API health is `ok`, readiness is `ready`,
  migration is `2d4e6f8a0b13 (head)`, graph invariants are valid at 45 checked nodes / 32 checked
  edges, and `/`, `/graph`, `/graph/system` all return HTTP 200. Recent API/worker/frontend logs have
  no error signature. Session: `AI_LOGS/SESSIONS/2026-08-11-1521-run-local-project.md`.
- On 2026-08-11 intake #70 / normal story `US-SYSTEM-MAP-PROGRESSIVE-TYPES` brought the separate
  Business AI Agents system map into the explicit-type/progressive-board contract requested by the
  owner. Initial canvas now shows only the system root and eleven collapsed `SYSTEM PILLAR` cards;
  the generic `BOARD` header is gone. Opening Data, Knowledge & Memory renders its 33 direct nodes
  inside that compound board while every other pillar stays visible and collapsed; closing returns
  to 12 cards. The inspector formats `SystemPillar` as `System Pillar`. Canonical API data remains
  complete and unchanged. Live Chrome proves `12 → 45 → 12`, all 33 children contained and zero
  errors; ESLint, TypeScript, 138/138 tests, build and responsive Playwright 3/3 pass. Intervention
  #25 records the correction and standard trace #71 holds the proof. Runtime is live at frontend
  `13000` / API `18000`. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1418-system-map-progressive-types.md`.
- On 2026-08-11 intake #69 / normal story `US-KNOWLEDGE-GRAPH-HOVER-TYPE` clarified the Network
  hover badge after the owner correctly rejected color as the only type cue. Network remains
  completely unlabeled at rest, while mouse hover or keyboard focus now reveals exactly one compact
  two-tier badge: explicit human-readable type in its semantic color above the node name. Hierarchy,
  Orbit, faint dashed overview edges and indexed direct-edge reveal are unchanged. Live Chrome on
  the rebuilt 429-node / 370-edge runtime proves visible type/name counts `0/0 → 1/1`, a real
  `COLLECTOR SOURCE` / `OpenAI News` badge, 68 direct edges and zero browser errors. ESLint,
  TypeScript, all 136 frontend tests, production build and responsive Playwright 3/3 pass.
  Intervention #24 records the correction and standard trace #70 holds the proof. Runtime is live
  at frontend `13000` / API `18000`.
  Session: `AI_LOGS/SESSIONS/2026-08-11-1345-network-hover-type.md`.
- On 2026-08-11 intake #68 / normal story `US-KNOWLEDGE-GRAPH-HOVER-LABELS` corrected the
  inconsistent Network naming reported by the owner. Semantic rank, degree and zoom no longer make
  any Network label visible at rest; all 429 labels/backdrops are uniformly hidden. Mouse hover or
  keyboard focus reveals exactly that one node's label, and leaving/blurring hides it again. Click
  selection retains neighborhood node/edge isolation but no longer exposes selected/neighbor label
  batches. The faint `0.08`-opacity dashed overview and indexed direct-edge reveal remain intact;
  Hierarchy/Orbit are unchanged. Live Chrome proves label counts `0 → 1 → 0`, zero selected-away
  labels, 68 direct edges on the highest-degree hover and zero browser errors. ESLint, TypeScript,
  all 136 frontend tests, production build, focused Harness 34/34, responsive Playwright 3/3,
  visual inspection and rebuilt readiness pass. Intervention #23 and standard trace #69 hold the
  correction/evidence. Runtime is live at frontend `13000` / API `18000`. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1153-network-hover-labels.md`.
- On 2026-08-11 intake #67 / normal story `US-KNOWLEDGE-GRAPH-EDGE-REVEAL` reduced Network
  connection clutter without hiding graph semantics. Resting Network edges remain selectable but
  render as `0.08`-opacity `3 7` dashed orientation lines; node hover reveals only its pre-indexed
  incident edges at `0.92` opacity as solid lines, and mouse leave restores the overview. Click
  selection still isolates the neighborhood; Hierarchy and Orbit are unchanged. On the real
  429-node / 370-edge runtime, the highest-degree node revealed exactly 68 connections and 50
  enter/leave cycles averaged 0.118 ms / max 0.8 ms with zero long tasks, transition owners,
  browser errors or residual reveal classes. ESLint, TypeScript, all 136 frontend tests, production
  build, focused Harness 34/34, responsive Playwright 3/3, visual inspection and rebuilt runtime
  readiness pass. Standard trace #68 holds the evidence. Runtime is live at frontend `13000` / API
  `18000`. Session: `AI_LOGS/SESSIONS/2026-08-11-1142-network-edge-reveal.md`.
- On 2026-08-11 intake #66 / normal story `US-KNOWLEDGE-GRAPH-HOVER-PAINT-PERF` corrected the
  remaining Network pointer lag that the prior JavaScript-only benchmark missed. Hover now changes
  only the pointed node/label or edge; corpus dimming is reserved for intentional click selection.
  The 429-node force layout settles once before display and stays stopped, delayed fit animations,
  inherited cursor writes and relationship SVG filters were removed. Live Chrome on 429 nodes / 370
  edges measured forced-style hover at 0.068 ms average / 0.4 ms maximum and frames at 16.357 ms
  average / 16.8 ms maximum, with zero post-switch long tasks, D3 transition owners or browser
  errors and a stable layout. ESLint, TypeScript, all 136 frontend tests, production build, focused
  Harness 34/34, responsive Playwright 3/3 and rebuilt runtime readiness pass. Owner correction
  intervention #22 and standard trace #67 hold the evidence. Runtime remains live at frontend
  `13000` / API `18000`. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1133-network-hover-paint.md`.
- On 2026-08-11 intake #65 / normal story `US-KNOWLEDGE-GRAPH-NETWORK-HOVER-PERF` fixed the
  owner-reported Network hover lag. Pointer focus no longer creates transitions or performs repeated
  full passes across 429 nodes / 370 edges: adjacency and incident edges are pre-indexed, a single
  SVG root class dims unrelated elements, and only the previous/current focus neighborhood receives
  direct class updates. Real Chrome completed 100 enter/leave cycles in 3.50 ms total (0.035 ms
  average) with zero node/edge transition owners and zero browser errors. Toolbar icons are now 9
  px, zoom icons 10 px, guide icons 12 px and painted node bases 8–15 px; invisible hit targets stay
  44 px. ESLint, TypeScript, 31 files / 136 tests, build, focused Harness 34/34, responsive
  Playwright 3/3 and rebuilt runtime health pass. Harness trace #66 meets the normal-lane standard
  tier. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1107-network-hover-performance.md`.
- On 2026-08-11 intake #64 / normal story `US-KNOWLEDGE-GRAPH-LIGHT-CANVAS` applied the owner's
  visual refinement to `/graph`: the studio, toolbar, canvas grid, Explorer, guide, inspector and
  status bar now use a cohesive white/light palette. Toolbar icons are capped at 11 px, zoom icons
  at 12 px, and Network/Orbit glyph bases were reduced from 14–22 px to 10–18 px with a smaller
  degree bonus. Compact glyphs retain invisible minimum 44 px hit targets, so mouse/touch selection
  remains reliable. Computed-style browser proof, live screenshot, ESLint, TypeScript, 31 files /
  135 tests, production build, focused Harness verification 33/33 and desktop/tablet/mobile
  Playwright 3/3 pass. Rebuilt runtime is live on frontend `13000`; proxied health/readiness and
  `/graph` HTTP 200 pass. Harness trace #65 meets the normal-lane standard tier. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1047-light-graph-canvas.md`.
- On 2026-08-11 intake #63 / normal story `US-KNOWLEDGE-GRAPH-GITNEXUS-EXPLORER` upgraded
  `/graph` into a GitNexus-inspired dark graph studio. Users can switch among clustered Network,
  progressive Hierarchy boards and deterministic Orbit layouts. Dense hierarchy parents now show
  four representative direct leaves plus a hidden count and expand/collapse locally; accepted
  semantic relationships between visible cards remain present as dashed cross-links. Real data
  initially renders 27 hierarchy cards, 16 semantic links and hides 64 leaves; expansion renders 91
  cards and 80 semantic links, while Network/Orbit retain all 429 bounded nodes. Frontend lint,
  TypeScript, 31 files / 134 tests, production build, focused Harness verification 32/32 and
  desktop/tablet/mobile Playwright 3/3 pass. Runtime is live on frontend `13000` and API `18000`;
  direct/proxied health and `/graph` HTTP 200 pass. The 338 approved-but-unplaced nodes remain an
  honest source-data curation item, not a renderer defect. Harness trace #64 meets the normal-lane
  standard tier. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1028-gitnexus-graph-studio.md`.
- On 2026-08-11 restarted the existing four-service local stack from its current images without
  rebuilding or changing application code/data. The documented conflict-free override remains API
  `18000`, frontend `13000`, and CORS origin `http://localhost:13000`. PostgreSQL is healthy; API,
  worker and frontend are running; direct/proxied health are `ok`; frontend `/` and `/graph` return
  HTTP 200; readiness is `ready`; migration is `2d4e6f8a0b13 (head)`; and the canonical system graph
  is valid at 45 nodes / 32 edges. Fresh API, worker and frontend logs contain no error signature.
  Session: `AI_LOGS/SESSIONS/2026-08-11-0943-start-local-project.md`.
- On 2026-08-10 intake #62 / normal story `US-KNOWLEDGE-GRAPH-VISUAL-REDESIGN` redesigned the
  research graph around progressive disclosure. Hierarchy now renders a readable multi-column
  branch atlas for the 91 connected research nodes and explicitly reports the other 338 approved
  nodes as unplaced; relationship retains all 429 nodes, limits overview labels to 26 meaningful
  hubs and emphasizes selected neighborhoods. The canvas is primary, explorer controls are
  optional, and the inspector floats only when needed. Frontend 130/130, lint/typecheck/build,
  responsive Playwright 6/6, live three-viewport overflow/console audit and rebuilt Compose
  health/readiness all pass on `13000`/`18000`. API, schema, data and governance are unchanged.
  Session: `AI_LOGS/SESSIONS/2026-08-10-2350-knowledge-graph-visual-redesign.md`.
- On 2026-08-10 restarted the existing four-service local stack without rebuilding images or
  changing application code/data. The documented conflict-free override remains API `18000`,
  frontend `13000`, and CORS origin `http://localhost:13000` because the unrelated Smart Exam
  backend owns port `8000`. PostgreSQL is healthy; API, worker and frontend are running; direct and
  proxied health are `ok`; frontend `/` returns HTTP 200; readiness is `ready`; migration is
  `2d4e6f8a0b13 (head)`; and the canonical graph is valid at 45 nodes / 32 edges. The fresh API,
  worker and frontend log scan found no error signature. Session:
  `AI_LOGS/SESSIONS/2026-08-10-2309-start-local-project.md`.
- On 2026-08-09 intake #61 / high-risk story `US-DOCUMENT-KNOWLEDGE-GRAPH-WORKSPACE` /
  DEC-053 completed the Document Workspace graph-analysis slice. Every readable upload now builds an
  isolated graph independent of paper-fit routing; `View analysis` deep-links to it; node inspection
  separates a source-grounded summary (hard cap 200 characters), independent AI research and an
  explicit consistency/difference result. Researchers can research one node or the graph and prepare
  a draft change set, but canonical publication still requires validate/review/approve/apply.
  Relationship and hierarchy now use the same approved research node corpus, the browser requests
  the explicit 1,000-node/4,000-edge safety bound, and the Business AI Agents system ontology is
  separate at `/graph/system`. Backend 316/316, frontend 123/123, lint/type/build, focused Playwright
  2/2, Compose readiness, migration head and runtime projection parity pass. Runtime is live on API
  `18000` and frontend `13000`; Harness story completion passed and detailed trace #62 meets tier
  3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-09-2254-document-knowledge-graph-workspace.md`.
- On 2026-08-09 restarted the existing four-service local stack without rebuilding images or
  changing application code/data. The documented conflict-free override remains API `18000`,
  frontend `13000`, and CORS origin `http://localhost:13000`. PostgreSQL is healthy; API, worker
  and frontend are running; direct and proxied health are `ok`; frontend `/` returns HTTP 200;
  readiness is `ready`; migration is `2d4e6f8a0b13 (head)`; and the canonical graph is valid at
  45 nodes / 32 edges. The fresh API, worker and frontend log scan found no error signature.
  Session: `AI_LOGS/SESSIONS/2026-08-09-2210-start-local-project.md`.
- On 2026-08-09 intake #60 / high-risk story `US-FRONTEND-FULL-DEFECT-SWEEP` completed the
  requested frontend-wide defect audit and fixed both reproducible frontend-owned failures. The
  standard Playwright command no longer collides with stale root-owned workspace artifacts, and the
  selected Graph inspector no longer expands a 1280 px page to 1287 px. ESLint, TypeScript, 29
  Vitest files / 122 tests, the 14-route production build and full Playwright run pass (66 passed;
  six auth cases expectedly skipped because the current local runtime has auth disabled). A
  separate real-data audit checked 13 routes across three viewports, 39/39 clean for status,
  console/page/API errors, untranslated badges and page overflow. Runtime remains healthy on
  `18000`/`13000`. Detailed Harness trace #61 meets the required tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1602-frontend-full-defect-sweep.md`.
- On 2026-08-09 intake #59 / normal story `US-DOCUMENT-LIST-OPEN-EDITOR` fixed the missing
  list-to-editor navigation reported by the owner. Uploaded filenames are now keyboard-accessible
  links to `/documents/{id}` and the misleading `View analysis` primary action is now `Open
  document` / `Mở tài liệu`; download and research remain separate actions. The initial browser
  regression test failed because no filename link existed, then passed on desktop/tablet/mobile.
  Full frontend 121/121, focused navigation/editor 11/11, ESLint, TypeScript and the
  complete Document Playwright suite 24/24 pass. A live click on the existing 40,222-character DOCX
  opened its non-readonly editor with zero console errors. Trace #60 meets standard tier 2/3 and
  owner correction intervention #21 records the previously missed entry path. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1532-open-uploaded-document-editor.md`.
- On 2026-08-09 intake #58 / normal story `US-LATEX-PREVIEW-DISPLAY-FIX` fixed the Document
  workspace PDF display regression. Compiled LaTeX and uploaded-original PDF iframes now request
  whole-page `Fit` instead of width-only `FitH`; changing LaTeX source immediately clears the stale
  compiled iframe, shows the compiling fallback, cancels the obsolete request and revokes discarded
  object URLs. The bounded XeLaTeX compiler and immutable uploaded-original contract are unchanged.
  Focused frontend tests 32/32, ESLint, TypeScript and LaTeX Playwright 9/9 pass across desktop,
  tablet and mobile; runtime remains available on `18000`/`13000`. Arbitrary PDFs continue to edit
  as labelled extracted-text derivatives, while LaTeX editing is reserved for actual `.tex` source.
  Harness trace #59 meets the normal-lane standard tier 2/3. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1512-fix-latex-pdf-preview.md`.
- On 2026-08-09 intake #57 / high-risk story `US-DOCUMENT-UPLOADED-EDITING` / DEC-052 completed
  view/edit support for every successfully extracted uploaded document. PDF/DOCX now preserve the
  immutable original for inline PDF viewing or original download while exposing canonical extracted
  text as a clearly labelled, immutable-versioned derivative. Save/AI edit/restore retain optimistic
  concurrency and re-enter processing/RAG; the worker treats later binary-workspace versions as
  UTF-8 text, never fake PDF/DOCX bytes. Backend 313/313, frontend 118/118, Ruff, ESLint, TypeScript,
  14-route build and Document Playwright 21/21 pass. Live existing-DOCX proof shows a 40,222-character
  editor, preserved original link and no horizontal overflow; runtime is healthy on `18000`/`13000`.
  Detailed Harness trace #58 meets the required tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1458-edit-uploaded-documents.md`.
- On 2026-08-09 restarted the existing four-service local stack without rebuilding images or
  changing application code/data. The documented host-port override remains required because the
  unrelated `smart_exam_backend` owns port `8000`: API `18000`, frontend `13000`, CORS origin
  `http://localhost:13000`. PostgreSQL is healthy; API, worker and frontend are running; direct and
  proxied health return HTTP 200; frontend `/` returns HTTP 200; readiness is `ready`; migration is
  `2d4e6f8a0b13 (head)`; and the canonical graph is valid at 45 nodes / 32 edges. Fresh API, worker
  and frontend logs contain no error, exception, traceback, fatal or HTTP 500 entry. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1427-start-local-project.md`.
- On 2026-08-07 fixed the reported regression in `US-DOCUMENT-FOCUS-EDIT-WINDOW` (intake #56): closing
  the two-pane edit window while a reviewed AI edit was pending left `instantEdit.pending` set, so the
  selection popover stopped appearing. `closeFocusWindow` now also discards the pending review (both
  `DocumentAuthoring` and `DocumentAIEditor`), and regression tests cover re-selecting after close.
  Frontend 117/117, ESLint, TypeScript pass; rebuilt live on `13000`. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1645-fix-selection-options-after-window-close.md`.
- On 2026-08-07 intake #56 / normal story `US-DOCUMENT-FOCUS-EDIT-WINDOW` / DEC-051 replaced the
  always-visible brainstorm panel with a ChatGPT-Canvas-like flow: initial view shows only the document
  content; selection popover options open a full-screen two-pane window (left: editable text, right:
  chatbot) with ✕/Escape close; edits persist after exit; the chatbot pane has a per-document
  "Chat history" toggle (localStorage, New chat + session reload). Frontend 115/115, ESLint, TypeScript
  pass; image rebuilt live on `13000`. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1640-focus-edit-window-chat-history.md`.
- On 2026-08-07 intake #55 / normal story `US-DOCUMENT-SELECTION-CHAT-ROUTING` / DEC-050 made
  selection actions surface in the brainstorm chat panel instead of popping a review card below the
  editor (ChatGPT-Canvas-like flow). Popover options post a user message in the chat and the reviewed
  AI edit card (diff + Accept/Reject, Undo, Retry) renders inside the chat thread; "Ask AI" and the
  pane-title edit button focus the chat composer; below-editor feedback and the `document-custom-ai`
  input were removed. Frontend was rebuilt and is live on `13000`; focused 20/20 (15 authoring + 5
  ai-editor) plus new routing test, TypeScript and ESLint pass. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1330-selection-actions-into-chat-panel.md`.
- On 2026-08-07 the polished Document UI was rebuilt live: frontend image rebuilt after Docker
  build-cache prune (full API rebuild hit disk-full on TeX layers). Stack is up on API `18000` /
  frontend `13000`; health/proxy/`/documents` return HTTP 200 and served CSS includes the new
  brainstorm polish classes. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1110-rebuild-document-ui-runtime.md`.
- On 2026-08-07 intake #54 / normal story `US-DOCUMENT-UI-POLISH` refreshed Document workspace UI:
  elevated authoring card, sticky polished brainstorm panel with avatars/bubbles, smoother
  Accept/Reject review cards, selection popover and micro-motion (reduced-motion safe). No AI/edit
  contract changes. Frontend focused 27/27, ESLint and TypeScript pass. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1048-document-ui-polish.md`.
- On 2026-08-07 intake #53 / high-risk story `US-DOCUMENT-BRAINSTORM-HIDDEN-BUGS` / DEC-049 fixed
  remaining Document Brainstorm edge bugs while keeping manual edit + AI chat edit. Selection is
  normalized against current source; instant-edit `run` returns success; chat edit reports
  ready/failed/busy with local-only status messages; brainstorm send locks while busy and Apply locks
  while a reviewed patch is pending; advisory Apply refuses mutations that break standalone LaTeX.
  Frontend focused 27/27, ESLint, TypeScript and backend document brainstorm/instant-edit 20/20 pass.
  Session: `AI_LOGS/SESSIONS/2026-08-07-1035-document-brainstorm-hidden-bugs.md`.
- On 2026-08-04 intake #52 / intervention #20 / high-risk story
  `US-DOCUMENT-REDACTION-ROUNDTRIP` / DEC-048 fixed the next reported LaTeX failure. The accepted AI
  patch had copied `[REDACTED_PHONE]` / `[REDACTED_EMAIL]` into Raw, losing local contact values and
  causing XeLaTeX `Missing $ inserted` on the underscores. Document edits now use unique ephemeral
  cloud tokens, require each selected token exactly once, restore originals only inside the API and
  fail closed on any leaked/altered marker. Compile errors now expose a bounded safe line/reason.
  Backend 312/312 and Ruff pass. Real DeepSeek proved email/phone absent from its prompt but restored
  without markers in a standalone review-only patch; live compile reports `Line 1: Missing $
  inserted.`. ESLint, TypeScript and Playwright 18/18 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-2320-redaction-roundtrip-latex-errors.md`. Detailed Harness trace
  #57 meets the required tier 3/3.
- On 2026-08-04 intake #51 / intervention #19 / high-risk story
  `US-DOCUMENT-PROXY-LONG-SUCCESS` / DEC-047 corrected the repeated Document AI connection error.
  Live logs proved DeepSeek and the API succeeded in 131.115 seconds while the old 125-second Next
  rewrite proxy reset the socket first. HTTPX's 120-second setting is an inactivity timeout, not a
  wall-clock ceiling. The bounded proxy default is now 180 seconds, deploy-visible through Compose.
  Frontend was rebuilt/recreated on the required port `13000`; effective env/build both report
  `180000`, proxied health is `ok`, and a real post-restart DeepSeek rename returned HTTP 200 in 5.7
  seconds. Frontend 110/110, ESLint, TypeScript, 14-route build and Playwright 15/15 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-2301-document-proxy-180s.md`. Detailed Harness trace #56 meets the
  required tier 3/3.
- On 2026-08-04 intake #50 / intervention #18 / high-risk story
  `US-DOCUMENT-LATEX-EDIT-INTEGRITY` / DEC-046 fixed the
  reported corruption path where a direct rename could replace complete LaTeX Raw source with AI
  explanation, Markdown headings and fenced snippets. Existing standalone whole-source LaTeX now
  requires another standalone document at both API and browser boundaries; malformed output gets
  typed safe feedback, no Accept action and no draft change. A real DeepSeek call through the
  frontend proxy returned a complete standalone document containing `Bùi Hoàng Linh` in 4.4 seconds
  with review still mandatory. Backend 307/307, Ruff, frontend 109/109, ESLint, TypeScript, 14-route
  build and Playwright 15/15 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-2230-latex-edit-source-integrity.md`. Detailed Harness trace #55
  meets the required tier 3/3.
- On 2026-08-04 intake #49 / intervention #17 / high-risk story
  `US-DOCUMENT-CHAT-EDIT-INTENT` / DEC-045 corrected
  contextual document chat so direct Vietnamese/English edit imperatives create structured reviewed
  patches instead of advisory prose. The current native selection is targeted, or the bounded whole
  source when no selection exists; full Original/Proposed content scrolls into view and Accept alone
  changes the local draft while Reject preserves it. Questions remain advisory Brainstorm. Live
  Chrome proved `sửa tên thành Bùi Hoàng Linh` made one instant-edit call and zero brainstorm calls,
  Reject retained `NGUYỄN MINH AN`, and Accept produced `BÙI HOÀNG LINH`; real DeepSeek returned a
  complete review-only LaTeX patch in 11.4 seconds. Backend 11/11, Ruff, ESLint, TypeScript, frontend
  106/106, 14-route build and Playwright 12/12 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1659-document-chat-reviewed-edits.md`. Detailed Harness trace #54
  meets the required tier 3/3.
- On 2026-08-04 intake #48 / intervention #16 / high-risk story
  `US-DOCUMENT-BRAINSTORM-RELIABILITY` / DEC-044 fixed
  the Document Brainstorm timeout UX reported from the LaTeX editor. Live telemetry proved the
  browser proxy stayed connected and DeepSeek itself reached the 120-second deadline. Typed
  provider/transport failures now render localized safe copy, retain the exact question and expose
  one explicit user-triggered Retry without duplicating the user bubble or automatically repeating
  a paid call. Rebuilt live Chrome injected the timeout and proved zero raw provider text, two total
  calls after Retry and one visible question; a real DeepSeek LaTeX name-change request then returned
  HTTP 200 in 3.3 seconds. Backend brainstorm tests 4/4, Ruff, ESLint, TypeScript, frontend 104/104,
  14-route build and Playwright 12/12 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1628-document-brainstorm-timeout-retry.md`. Detailed Harness trace
  #53 meets the required tier 3/3.
- On 2026-08-04 the Document AI "connection interrupted" report was traced to stale runtime
  configuration, not the browser proxy or LaTeX preview. The running API container had no
  DeepSeek credential while `GRAPH_CHAT_DEFAULT_PROVIDER=deepseek`, so each instant-edit request
  failed immediately with typed HTTP 503. The current `.env` already contained the credential;
  recreating API and worker synchronized it without changing application code or data. Provider
  status now reports DeepSeek configured, and a real rewrite through the frontend proxy returned
  HTTP 200 in 9.9 seconds with a review-only replacement. API health is `ok`; fresh logs contain
  no provider error or proxy reset. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1459-restore-document-ai-provider.md`.
- On 2026-08-04 intake #47 / intervention #15 / high-risk story `US-LATEX-OVERLEAF-PREVIEW` / DEC-043 replaced the
  heuristic-only LaTeX output with a real XeLaTeX PDF preview. The debounced browser request embeds
  the compiled PDF and keeps the prior safe renderer only for loading/error fallback. Compilation
  is ephemeral, `no-shell-escape`, rate-limited and bounded by source/output, timeout, CPU, memory,
  file, descriptor and process limits. The API image now includes XeLaTeX, LaTeX Extra,
  recommended/extra fonts and Noto. Live Chrome compiled and displayed a two-column CV with custom
  macros, skill bars, Vietnamese, Font Awesome and Noto Sans. Ruff, 301 backend tests, ESLint,
  TypeScript, 103 frontend tests, 14-route build and 12/12 document Playwright cases pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1424-overleaf-latex-pdf-preview.md`. Detailed Harness trace #52
  meets the required tier 3/3.
- On 2026-08-04 intake #45 / intervention #14 / normal story `US-LATEX-PREVIEW-CV-SEMANTIC-MACROS` corrected the
  remaining CV-template macro leakage: `mainsection` maps to a section heading, `jobheading` maps
  to a role plus date/employer line, and tight bullet delimiters control clean list items. Live
  Chrome renders the work-experience section without raw macro names. ESLint, TypeScript, 103
  frontend tests, 14-route build and 12/12 document Playwright cases pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1338-latex-preview-cv-semantic-macros.md`.
- On 2026-08-04 intake #44 / intervention #13 / normal story `US-LATEX-PREVIEW-LAYOUT-MACROS` corrected the remaining
  safe Preview leakage reported from a CV: body-level layout commands such as `sidesection`, font,
  color, spacing, minipage and alignment syntax are now removed rather than displayed as prose,
  while their readable heading/text survives. Live Chrome imported an owner-style CV fixture and
  showed only its rendered content with no residual macro names. ESLint, TypeScript, 102 frontend
  tests, 14-route build and 12/12 document Playwright cases pass. Preview remains a safe browser
  renderer, not a XeLaTeX compiler. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1310-latex-preview-layout-macros.md`.
- On 2026-08-04 intake #43 / intervention #12 / normal story `US-LATEX-PREVIEW-PREAMBLE` corrected the apparent
  LaTeX compilation failure in Preview. The runtime has no TeX engine, so Preview is intentionally
  a safe browser markup renderer rather than a compiler. It now removes everything before
  `\\begin{document}` and after `\\end{document}`, hides comments and non-content formatting
  commands, and displays body headings/text only. Live Chrome showed the XeLaTeX-style ALOHA source
  as a clean page without `usepackage`, `setmainfont` or compiler comments. ESLint, TypeScript, 101
  frontend tests, 14-route build and 9/9 document Playwright cases pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1246-latex-preview-body.md`.
- On 2026-08-04 intake #42 / intervention #11 / normal story `US-DOCUMENT-PREVIEW-RAW-WRAP` corrected the first
  preview-overflow fix after owner feedback: Raw had an internal horizontal scrollbar rather than
  visually wrapping. Raw now uses preserved newlines plus safe word wrapping for long LaTeX commands,
  URLs and unbroken content, with vertical-only scrolling. Live Chrome rendered long Vietnamese
  LaTeX source at 1920px, 1024px and 390px with no pane or page horizontal overflow. ESLint,
  TypeScript, 100 frontend tests, 14-route build and 9/9 document Playwright cases pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1142-document-raw-wrap.md`.
- On 2026-08-04 intake #41 / intervention #10 / normal story `US-DOCUMENT-PREVIEW-OVERLEAF` corrected the collapsed
  `Preview document` surface. Raw source now has an explicit bounded internal scroll region for
  long unbroken lines; split mode gives rendered Preview 64% of the width and renders it as a larger
  centered white paper canvas on a quiet gray workspace, inspired by Overleaf. The same component
  treatment applies in authoring and uploaded-source editor previews, then stacks at tablet/mobile.
  Live Chrome proved a 12,000-character Raw line causes no document-level horizontal overflow across
  desktop/tablet/mobile; ESLint, TypeScript, 100 frontend tests, 14-route build and 9/9 document
  Playwright cases pass. Session log:
  `AI_LOGS/SESSIONS/2026-08-04-1136-document-preview-overleaf.md`.
- On 2026-08-04 owner correction intake #40 / intervention #9 / high-risk story
  `US-DOCUMENT-AI-EDIT-REVIEW` / DEC-042 superseded automatic low/medium-risk local AI edits. Every
  changed patch now shows the complete original/replacement diff and requires explicit Accept or
  Reject; the draft remains unchanged while review is pending and stale responses still fail
  closed. Provider instructions now make the user's transformation mandatory over the complete
  selection, repeat it after bounded context, and enforce verifiable LaTeX output contracts. A live
  DeepSeek smoke first reproduced the false no-change behavior, then returned HTTP 200 with a
  complete standalone LaTeX document and `auto_apply_allowed=false` after the fix. All 296 backend
  tests, Ruff, ESLint, TypeScript, 100 frontend tests, the 14-route build, 9/9 responsive Playwright
  cases and `git diff --check` pass. Full-tree Ruff format-only still reports 36 unrelated
  pre-existing files; both changed backend files pass focused formatting. Session log:
  `AI_LOGS/SESSIONS/2026-08-04-1112-reviewed-document-ai-edits.md`.
- On 2026-08-03 owner correction intake #39 / high-risk story
  `US-DOCUMENT-AI-EDIT-RELIABILITY` / intervention #8 / DEC-041 fixed the live instant-edit 500 and
  simplified Document workspace. Runtime evidence showed DeepSeek completing successfully at the
  API in 33.8 seconds after Next.js's default 30-second rewrite proxy had already reset the browser
  socket. The proxy budget is now 125 seconds, above the API's 120-second provider deadline;
  malformed payloads become typed 502 errors, transient failures have localized safe-copy plus one
  explicit Retry, and no-change/auth/rate-limit cases no longer display raw HTTP text. The authoring
  page now prioritizes title/format/import, editor + AI and Create: duplicated descriptions and the
  upload-policy card are gone; PDF/DOCX upload and Raw/Preview/Side-by-side inspection are compact
  collapsed disclosures. Ruff and all 295 backend tests, ESLint, TypeScript, all 99 frontend tests,
  the 14-route build and 9/9 responsive Playwright cases pass. A real DeepSeek call through the
  rebuilt frontend proxy returned HTTP 200, runtime health/readiness and the 45-node/32-edge graph
  remain valid, and recent logs are clean. Session log:
  `AI_LOGS/SESSIONS/2026-08-03-0026-document-ai-reliability-simple-ui.md`. Detailed Harness trace
  #45 meets the required high-risk tier 3/3.
- On 2026-08-02 intake #38 / high-risk story `US-DOCUMENT-INSTANT-AI-EDIT` / DEC-040 changed
  selected-text AI assistance from a persisted proposal/Accept workflow to conflict-safe direct
  editing of the local document draft. Both the pre-create authoring surface and uploaded editable
  source now expose Improve, Shorten, Expand, Fix grammar and custom instructions from native text
  selection, plus a paragraph fallback. Low/medium-risk prose replaces the exact selected range
  immediately with Undo and View diff; numbers, citations, URLs, code/formulas, semantic-change
  requests and cloud-redacted input fail into explicit review-only Apply/Discard. Every response is
  bound to the full source revision, range and original text; a changed draft or selection rejects
  the late patch. Provider calls are bounded, redacted, structured, rate-limited, tool-free and
  persistence-free. Create/Save remains the only durable version and RAG trigger. Ruff and all 294
  backend tests, ESLint, TypeScript, all 94 frontend tests, the 14-route build and 9/9 responsive
  Playwright cases pass. Rebuilt runtime is healthy on `18000`/`13000`, readiness and the 45-node /
  32-edge graph are valid, and recent logs are clean. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-2318-document-instant-ai-edit.md`. Detailed Harness trace #44
  meets the required high-risk tier 3/3.
- On 2026-08-02 intake #37 / high-risk story `US-DOCUMENT-UNIFIED-EDITOR-CHAT` / DEC-039
  unified editable import and contextual AI brainstorming inside Document workspace. Markdown,
  TXT, LaTeX, reStructuredText, AsciiDoc and HTML files can now be imported directly into the
  F5-safe `Document content` draft, reviewed/edited before governed creation, and remain editable
  after upload through immutable versions. PDF/DOCX remain bounded binary references to avoid a
  lossy rich-document round trip. A stateless, bounded and redacted DeepSeek/OpenAI endpoint powers
  chat beside both the pre-create editor and uploaded source editor; responses render as sanitized
  Markdown and never modify text until the user explicitly chooses Replace selection, Insert at
  cursor or Append. Create/Save remains separate. The wide layout is editor/chat side-by-side and
  stacks without horizontal overflow at Windows/tablet/mobile widths. Fresh Harness proof passes:
  Ruff, all 289 backend tests, ESLint, TypeScript, 88/88 frontend tests, 14-route build and 9/9
  responsive Playwright cases. The rebuilt API/worker/frontend are healthy on `18000`/`13000`,
  `/documents` is HTTP 200 and recent logs are clean. Detailed Harness trace #43 meets the required
  high-risk tier 3/3. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-2213-document-unified-editor-brainstorm.md`.
- On 2026-08-02 owner correction intake #36 / high-risk story
  `US-SELECTION-ACTIONS-WINDOWS-LAYOUT` / DEC-038 fixed the missing selection interaction and dense
  Windows layout. Native selection in Markdown/TXT source now opens Improve/Shorten/Expand/Fix
  grammar/Ask AI next to the selected range; its provider result remains a proposal until Accept.
  Native selection inside one Brainstorm message opens Ask AI/Explain/Summarize; an action only
  prepares a bounded Markdown quote in the local composer and never sends or mutates history. For a
  closed session it also opens the existing new-chat form, leaving Send disabled until an active
  session exists. `/chat` is now two columns (session history + primary thread); redundant Graph
  context/Knowledge changes/Tool activity cards are gone, scope/provider/status are compact header
  chips and graph review links remain inline. Viewport height keeps the composer visible, session
  horizontal overflow is eliminated, and the topbar uses aria-labeled/title icons at widths ≤1440
  instead of clipping routes. ESLint, TypeScript, 84/84 frontend tests, 14-route build and 15/15
  Playwright cases pass across desktop/tablet/mobile plus explicit 1366×768 and 1920×1080 checks.
  Live Chrome visually proved both popovers; rebuilt runtime health/proxy/chat are HTTP 200 and fresh
  logs are clean. Harness fresh proof passed and detailed trace #42 meets high-risk tier 3/3. No
  backend/schema/provider/audit behavior changed. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-2020-selection-actions-windows-chat-layout.md`.
- On 2026-08-02 intake #35 / high-risk story `US-DOCUMENT-AI-EDIT-RAG` / DEC-037 completed
  ChatGPT-style inline assistance in uploaded Markdown/TXT documents. Owners/researchers can edit
  Raw/Preview/Side-by-side, select text for Improve/Shorten/Expand/Fix grammar/custom proposals,
  compare original/replacement, and explicitly Accept or Reject. AI never auto-applies. Manual
  save, Accept and restore create immutable object-backed source versions with optimistic version
  and selection-hash conflicts; a per-user/workspace/version local cache survives F5. Every
  processed upload/version now refreshes document-scoped pgvector chunks automatically; draft rows
  are excluded from global approved search, RAG failures are independently visible/retryable, and
  stale document graph/evidence is removed before a changed version is evaluated. Migration
  `2d4e6f8a0b13` is live after `/tmp/research-pre-document-ai-edit.dump`; it backfilled version 1
  for three existing workspaces without copying/deleting source bytes. Those legacy workspaces are
  intentionally `pending` until individual RAG rebuild; new uploads/versions are automatic. Ruff,
  55 focused and 285 full backend tests, ESLint, TypeScript, 83 frontend tests, 14-route build,
  9/9 desktop/tablet/mobile Playwright cases and Harness fresh proof pass. API/worker/frontend are
  healthy on `18000`/`13000`, graph remains valid at 45 nodes / 32 edges, and fresh API/worker logs
  are clean. DOCX/PDF rich editing remains a separate high-risk follow-up. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-1925-document-ai-edit-auto-rag.md`.
- On 2026-08-02 the existing four-service local stack was restarted without rebuilding images or
  changing application code/data. The documented host-port override remains required because the
  unrelated `smart_exam_backend` owns port `8000`: API `18000`, frontend `13000`, CORS origin
  `http://localhost:13000`. PostgreSQL is healthy; API, worker and frontend are running; direct and
  proxied health return `ok`; frontend `/` returns HTTP 200; readiness is `ready`; migration is
  `f8b3d1e6a204 (head)`; and the canonical graph is valid at 45 nodes / 32 edges. The fresh startup
  log scan found no error, exception, traceback, fatal or HTTP 500 entry. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-1820-start-local-project.md`.
- On 2026-08-01/02 intakes #33-34 / high-risk story `US-CHATGPT-SHARED-IMPORT` /
  DEC-035/036 added and corrected one-way public ChatGPT snapshot import in `/chat`. Exact official
  shares are fetched over the public anonymous boundary; visible text renders as sanitized GFM
  instead of raw Markdown. Current generated-image `sediment://file_*` records are retained as
  assistant media without raw tool text, resolved through ChatGPT's anonymous share asset endpoint,
  validated by public-peer/host/redirect/raster-MIME/image-count/per-image/aggregate-byte limits,
  retried twice for transient asset failures, and cached in object storage. Browsers receive only a
  same-origin media URL; signed URLs/object keys never enter provider history. Migration
  `f8b3d1e6a204` is live. Ruff and 280 backend tests pass; TypeScript, ESLint, 80 frontend tests,
  the 14-route build and 6/6 responsive Playwright cases pass. A live current-format public share
  proved 5 visible messages / 1 cached 2,475,962-byte PNG and the rebuilt runtime completed the
  201 import → 200 local-image round trip on `18000/13000`. Four smoke sessions and their three
  objects were removed afterward. Existing imports that discarded pointers require re-import.
  Session logs: `AI_LOGS/SESSIONS/2026-08-01-2308-chatgpt-shared-local-fork.md` and
  `AI_LOGS/SESSIONS/2026-08-02-0120-chatgpt-import-markdown-images.md`.
- On 2026-07-30 intake #31 / high-risk story `US-DOCUMENT-AUTHORING-CACHE` /
  `DEC-LOCAL-DOCUMENT-DRAFT-CACHE` added direct source authoring to `/documents`.
  Owners/researchers can type a title, choose Markdown, TXT, LaTeX, reStructuredText,
  AsciiDoc or HTML, inspect the existing safe Raw/Preview/Side-by-side view, and create the
  result through the governed multipart upload pipeline. A versioned two-million-character
  `localStorage` draft is scoped to the authenticated user, written on every edit, restored
  after F5/browser restart, retained after upload failure, and removed only after successful
  creation or explicit discard. Draft content is never logged or sent before Create. ESLint,
  TypeScript, 77/77 frontend tests, the 14-route production build, focused backend Markdown
  upload proof and 3/3 desktop/tablet/mobile Playwright refresh tests pass. Frontend was rebuilt;
  database/API/worker/frontend run on the existing `18000/13000` override. Full session log:
  `AI_LOGS/SESSIONS/2026-07-30-2338-document-authoring-cache.md`.
- On 2026-07-30 intake #30 / high-risk story `US-REMOVE-TRAINING-DATA` /
  `DEC-REMOVE-TRAINING-DATA` retired the Training Data Hub at the owner's explicit request.
  Frontend route `/training`, every `/api/v1/training/*` endpoint, authorization rules, localized
  UI copy, ORM models, seed behavior and feature tests were removed. Migration `e1f7a9c3b205`
  deleted all six tables (`training_events`, `training_examples`, `training_datasets`,
  `training_dataset_examples`, `preference_pairs`, `model_eval_runs`) from PostgreSQL, including
  the one example, one dataset and one membership row found before migration. Historical
  migrations/logs/source brainstorms remain as immutable audit history; the new migration and
  DEC-032 supersede their feature direction. Ruff, 256/256 backend tests, 71/71 frontend tests
  and the 14-route build pass. Rebuilt runtime checks show API `/training` and browser `/training`
  return 404, OpenAPI has zero retired paths, PostgreSQL has zero retired tables, and all four
  services run on the existing `18000/13000` override. Full session log:
  `AI_LOGS/SESSIONS/2026-07-30-2230-remove-training-data.md`.
- On 2026-07-30 intakes #28-29 / stories `US-DOCUMENT-EDITABLE-FORMATS` and
  `US-DOCUMENT-SCOPED-CHAT-CONTEXT` expanded Document workspace beyond its first-cut
  PDF/Markdown/TXT contract. The bounded upload set is now PDF, DOCX, UTF-8 TXT, Markdown,
  LaTeX, reStructuredText, AsciiDoc and HTML. DOCX containers require valid bounded OpenXML;
  source formats expose a separate raw view while canonical extracted text feeds paper-fit,
  isolated graph and document-scoped chat. `/documents/{id}` now offers safe Raw, Preview and
  Side-by-side modes without executing uploaded markup. Document chat receives only bounded
  canonical text, passed through the existing cloud-redaction and overall context limit; no raw
  bytes, new retention behavior or publish authority were added. Both Harness stories completed.
  Ruff and 257/257 backend tests pass; ESLint, TypeScript, 71/71 frontend tests and the 15-route
  build pass. API/worker/frontend images were rebuilt; health is `ok`, readiness is `ready`,
  graph remains valid at 45 nodes / 32 edges, and live Chrome proves the source viewer on a real
  Markdown workspace. Full session log:
  `AI_LOGS/SESSIONS/2026-07-30-2149-editable-document-workspace.md`.
- On 2026-07-30 intake #27 aligned the primary navigation with the owner's document-workspace
  task group. Desktop and mobile navigation now label `/documents` as `Document workspace`
  (`Không gian tài liệu` in Vietnamese) and no longer expose `Training data`. That initially
  non-destructive scope was superseded later the same day by intake #30 and DEC-032 above. The
  focused AppShell tests pass 2/2, ESLint and
  `tsc --noEmit` pass, and a live system-Chrome check on `/chat` confirms both navigation
  variants contain `Document workspace` and zero `Training data` links. Full session log:
  `AI_LOGS/SESSIONS/2026-07-30-2123-document-workspace-navigation.md`.
- On 2026-07-30 the existing four-service local stack was restarted without rebuilding images or
  changing application code/data. The repository `.env` still selects host ports `8000/3000`, so
  the documented runtime override was required because another project owns port `8000`:
  `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000`. PostgreSQL, API,
  worker and frontend are running; frontend `/` returns HTTP 200, API health is `ok`, readiness is
  `ready`, migration is `d8f3b1c6a247 (head)`, and the canonical graph is valid at 45 nodes /
  32 edges. Full session log:
  `AI_LOGS/SESSIONS/2026-07-30-1957-start-local-project.md`.
- On 2026-07-30 a UI/UX polish session improved the deep-ocean interface across every page
  without changing the accepted DEC-014/DEC-015 palette or any API/data/route/auth behavior.
  The graph workspace is the focus: the D3 hierarchy/relationship renderer gained SVG defs
  (drop-shadow, glow, edge gradients, node radial sheen), the canvas now sits on a layered
  radial-gradient with an inner highlight, the zoom control became frosted glass, the view
  switcher and toolbar/inspector buttons became pills with hover lift, breadcrumb and empty
 /loading states are highlighted, and hierarchy cards have deeper hover shadows. The app
  shell, dashboard hero, cards, badges, tables, research tabs, detail stats and evidence
  panel all received spacing/depth/motion refinement. Decisions introduced no new tokens
  (the undefined `--radius-md` that the old `graph-board-hint` relied on was fixed). ESLint,
  `tsc --noEmit`, 67/67 Vitest, the 15-route production build and 41/48 Playwright words
  pass with zero horizontal overflow on desktop/tablet/mobile. The single failing E2E
  (`graph-hierarchy > boards expand`, desktop only) was confirmed to fail identically on the
  clean git baseline, so it is a pre-existing flake, not a regression. Frontend `13000` and
  API `18000` are healthy. Full session log:
  `AI_LOGS/SESSIONS/2026-07-30-1055-ui-ux-graph-polish-deep-ocean.md`.

## Previous Goal

- On 2026-07-30 owner correction intervention #5 / intake #26 / high-risk story
  `US-DISCORD-AUTO-SUBMIT-PIN` / DEC-031 clarified and proved zero-command intake:
  posting a supported link/PDF in an allowlisted channel automatically invokes collection;
  `/submit` is optional only. The bot now has `/pin message_id:<id>`, restricted to the
  current allowlisted channel and gated by Discord's current `PIN_MESSAGES` permission for
  caller and bot. Invalid/cross-channel IDs do not broaden lookup, already-pinned messages
  are idempotent, the external mutation has a bounded actor audit reason, and no Research
  API scope was added. `discord.py` is bounded to `>=2.7.1,<3`. Full proof passes: 55
  gateway tests, Ruff lint/format, focused receipt→graph→gap backend proof, Compose,
  production image and actual callback smoke. Live pinning still needs owner credentials.
- On 2026-07-30 intake #25 / story `US-DISCORD-BOT-COMMAND-GUIDE` made the Discord
  gateway discoverable like a normal bot. It now exposes allowlist-gated `/help`, `/guide`,
  `/sources`, `/ping`, `/submit` and `/status`; includes bilingual source/limit, review,
  graph and knowledge-gap guidance; advertises `/help` in its presence; points empty
  mentions to help; handles unexpected command errors without leaking details; and copies
  the global command set into every configured guild before sync. A credential-free
  production-image smoke verifies all 6 commands. All 43 gateway tests, Ruff, Compose,
  image build and Harness completion pass. A live guild still needs owner-held Discord
  credentials.
- On 2026-07-30 intake #24 / story `US-DISCORD-BOT-TEST-RUNBOOK` added the executable
  Vietnamese test guide `Docs/Discord Bot Test Runbook.md`. It covers Discord application
  setup and Message Content intent, minimum permissions, allowlist IDs, a two-scope service
  account, secret-safe local configuration, automated and live acceptance cases, receipt /
  relationship-graph / knowledge-gap evidence, troubleshooting, revoke and cleanup. Static
  doc checks, Compose config, 36 gateway tests, the focused backend graph-gap proof and the
  Discord image build pass. The story is implemented; only the owner's live guild run needs
  a Discord bot token and allowlisted server/channel IDs.
- On 2026-07-30 intake #23 / story `US-DISCORD-GAP-ALERTS` / DEC-030 extended the already-built
  Discord gateway for the requested zero-touch link path. Discord URL receipt items request guarded
  auto-approval by default; the API retains complete-source and confidence gates, approval refreshes
  persisted low-coverage gaps, and namespace-scoped receipt reads expose only related active gaps
  for a bounded bilingual channel alert. Complete eligible links appear in the approved
  relationship graph and create the existing governed hierarchy change-set proposal; the bot still
  cannot approve/apply canonical graph changes or manage gaps. Full proof passes: 252 backend, 36
  gateway and 67 frontend tests, Ruff/ESLint, Compose config and the Discord image build. No local
  Compose stack was running, and real Discord delivery still needs the owner's bot token plus
  guild/channel allowlist.
- On 2026-07-29 intake #21 added a shared footer, then owner correction intake #22 / intervention
  #4 removed its nonessential landing-style content. The final `AppShell` footer is a compact dark
  bar containing only `Research System`, three core links (Research, Sources, Knowledge graph) and
  copyright; it wraps cleanly on mobile. ESLint, TypeScript, 67 frontend tests, the 15-route
  production build and three-viewport Playwright proof pass with no horizontal overflow.
- On 2026-07-26 Linh set a new completion objective and authorized a fixing loop through the
  Harness (intake #19). The contract is `Docs/Business AI Agents Completion Goal.md`, covering
  five areas: (A) link intake reaching the knowledge hierarchy, (B) actionable link-extraction
  failures, (C) graph display and navigation, (D) the Discord intake bot, (E) cross-cutting
  quality. Linh reprioritized Discord: it is now inside the goal rather than deferred behind
  the earlier completion gates.
- On 2026-07-27 a follow-up defect sweep (intake #20, story `US-FULLSTACK-DEFECT-SWEEP`)
  found and fixed seven further issues, three of them in code written the previous day: the
  migration chain failed on SQLite, two URLs redirecting to one page crashed the worker on
  the unique URL index, five foreign keys had no index, duplicates predating
  `duplicate_of_id` were never backfilled, backlog counts came back as floats, an unknown
  status filter returned an empty list instead of refusing, and the E2E suite raced its
  workers. Totals are now 250 backend, 33 gateway and 66 frontend tests plus 39
  deterministic E2E cases; migration head is `d8f3b1c6a247` and every live integrity check
  reports zero.
- **The goal is fully implemented.** Every area (A, B, C, D, E) is complete, and all four
  completion stories passed `harness-cli story complete` running their real proof commands.
  Totals: 242 backend tests, 33 Discord gateway tests, 66 frontend tests, 9 three-viewport
  Playwright cases; ruff, eslint, tsc and the 15-route production build are clean. Migration
  head is `b6d9f1a3c527`. The API and worker images were rebuilt and the stack is healthy on
  `18000`.
- What remains is owner decisions, not engineering: review link change set
  `42ae7795-280e-4ee1-8525-2462cc061074`; replace or remove the OpenAI credential the new
  preflight shows as not answering; supply a Discord token and channel allowlist to run the
  gateway for real.
- The Discord gateway lives at `apps/discord-bot` behind the `discord` Compose profile. It
  is a thin adapter per DEC-028: allowlist closed by default, scoped to `intake:submit` and
  `intake:read-own`, and all 36 of its tests run without Discord or a network.
- Areas A1-A5, B1-B9, B11, B12, C1-C5 and E1 were complete and verified earlier in the day. A submitted URL now
  becomes a reviewable, evidence-backed set of canonical placements under the eleven pillars,
  proven on the live runtime with `https://arxiv.org/abs/2210.03629` producing change set
  `42ae7795-280e-4ee1-8525-2462cc061074` (16 mutations, 16 valid, 0 errors, 1 warning).
  Extraction failures carry a specific code and a bilingual next action; the review queue and
  its stranded duplicates are visible and recoverable; the hierarchy navigates to any depth and
  states exactly how much of a result it is showing. 215 backend tests and 48 frontend tests
  pass; ruff, tsc and eslint are clean. Migration head is `b6d9f1a3c527`.
- Two honest limitations are recorded in
  `AI_LOGS/SESSIONS/2026-07-26-2320-graph-polish-preflight-and-discord-gateway.md`:
  conditional-GET validators are not yet persisted between submissions, and host rate
  limiting is per worker process.
- The measured baseline that motivated the goal: 27 link submissions had produced only 3
  `ResearchItem` nodes, ten of eleven pillars were empty, one submission failed with an opaque
  `INTERNAL_ERROR`, and the worker logged failures without a cause.

## Previous Goal (still open for product-owner acceptance)

- Linh resumed the completion objective on 2026-07-21 and explicitly authorized DeepSeek as the
  temporary Graph Intelligence v2 chat provider, with later configuration-only OpenAI switchback:
  finish Graph v2 acceptance, complete Gate C non-local exposure, verify projections, and only then
  implement Discord.
- Immediate milestone: Linh reviews the real hierarchy and review change set
  `5759af2f-4685-4cfa-b360-39d7981a1fa4`, then records the product-owner decision in
  `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`.
- Người yêu cầu: Linh.
- Trạng thái: repository execution resumed under intake #14 and DEC-029, but the goal service still
  reports the previous goal as `blocked` and rejects a replacement goal while it is unfinished. The
  four-service stack is running on API `18000`/frontend `13000`.
  The non-chat Graph v2 walkthrough, Mistral hardening, routed MinIO attachment adapter,
  production-safe observability, local auth/RBAC, file-mounted secrets, bounded
  OCR/browser/Reel-transcript enrichment, Neo4j graph projection and Meilisearch/pgvector search
  projections, the copy-and-verify legacy-object migration tool, and the source-neutral receipt /
  scoped service-account application boundary are complete. Real chat/final product-owner
  acceptance now use a DeepSeek-first provider-neutral path; the live DeepSeek provider and
  draft-proposal proof are complete, while Linh's product decision remains pending. Secret-safe
  provider overlays, a generic operator preflight and executable acceptance verifier are ready; executing the object
  migration and remaining Gate C/D deployment policy are separately authorized external operations.

## Current State

- Discord's normal intake path requires no command: an ordinary allowlisted link/PDF
  message reaches `_collect`. `/pin` is the only newly mutating command and uses Discord
  permission/audit state, not the Research service account.
- The Discord bot's normal user entrypoint is now `/help`; `/guide` explains the complete
  source-to-graph flow, `/sources` states supported categories and access boundaries, and
  `/ping` reports gateway latency. `scripts/verify_discord_bot_commands.sh` verifies
  production-image registration and guild copying without loading real tokens.
- The Discord gateway now has one canonical operator path from account setup through sign-off:
  `Docs/Discord Bot Test Runbook.md`. It explicitly distinguishes a valid guarded-review result
  from failure and explains that hierarchy placements remain governed change sets.
- On 2026-07-25 intake #18 exported the verified requirement-by-requirement status into
  `Docs/Business AI Agents Project Status Report.md`. The Vietnamese report separates completed
  engineering, product-owner acceptance, OpenAI switchback, autonomous-research limits and
  production backlog; it introduces no product, API, data or provider behavior change.
- On 2026-07-25 correction intake #17 / completed story `US-GRAPH-COMPOUND-BOARDS` replaced the
  rejected external branch drilldown with the standards-based compound/folding interaction. The
  root and all collapsed sibling boards remain visible; clicking a board lazily loads its direct
  children and expands that same `SystemPillar` into a bounded group container. Every child card is
  geometrically inside the container, internal containment edges are hidden, and clicking the
  header collapses it. This changes only the projection, not canonical storage or governance.
  TypeScript, all 32 frontend tests, the 15-route build, 30 enabled full E2E cases across three
  viewports, focused Harness verification and live Chrome proof of the real 33-node board all pass.
  Frontend `13000` and API `18000` remain healthy, the settled browser has no console/page/HTTP-5xx
  errors, Harness trace #26 meets the normal-lane standard, and drift entropy is `0/100`.
- On 2026-07-25 intake #16 / story `US-GRAPH-BOARD-DRILLDOWN` implemented the intermediate external
  branch drilldown. Its query bounding and multi-column work remain useful, but intake #17 above
  supersedes its presentation because the owner required children to render inside the board while
  sibling boards remain visible.
- On 2026-07-25 API-container reachability to DeepSeek recovered. The secret-safe selected-provider
  preflight returned `ready` for `deepseek-v4-pro`; a real graph-scoped session exercised search and
  node-context tools. Broad turns stopped safely at `CHAT_TOOL_LOOP_LIMIT`, and an ungrounded
  proposal remained invalid. A clean document-scoped session then used source evidence plus
  `create_change_set` and `propose_node` to create review change set
  `5759af2f-4685-4cfa-b360-39d7981a1fa4`. Its one `Cited Recommendation Review Gate` mutation is
  evidence-supported and valid with zero errors or warnings. No canonical mutation was approved or
  applied. Only Linh's walkthrough and rollout decision remain for Graph v2 product acceptance;
  OpenAI switchback is optional follow-up.
- On 2026-07-25 owner correction intake #15 / completed normal story `US-GRAPH-HIERARCHY`
  aligned the main graph with the original parent-child sketch. `/graph` now defaults to a
  deterministic left-to-right hierarchy of readable cards and curved branches with explicit input
  and branch-focus ports; relationship mode remains secondary. Root view is bounded to
  `System → 11 pillars`; focused branches retain ancestor breadcrumb context, traverse only toward
  descendants, exclude sibling pillars and visibly report truncation. Hierarchy mode no longer runs
  force simulation. The API response shape, PostgreSQL source of truth and graph governance are
  unchanged.
- The five requested Graph Intelligence workflows have fresh combined proof: paper-fit evaluation,
  per-upload isolated document graph, canonical parent/child placement, the eleven-section system
  ontology and governed chat-to-draft-change-set flow. Ruff and 41 focused backend tests pass;
  frontend lint/typecheck, 29 tests and the 15-route production build pass; 15 document/hierarchy/
  chat/change-review E2E cases pass across desktop/tablet/mobile. API/frontend images were rebuilt,
  runtime is ready at 45 nodes / 32 edges and fresh logs are clean.
- On 2026-07-25 the existing four-service Research System stack was restarted without rebuilding or
  changing application code. PostgreSQL data and object volumes were preserved; database, API,
  worker and frontend are running on API `18000` / frontend `13000`. Direct and proxied health,
  frontend root, feature discovery and readiness pass; migration is at `a8b4c6d2e913` head and the
  canonical graph is valid at 45 nodes / 32 edges. Fresh startup logs are clean and all unrelated
  `smart_exam_*` containers remained running and untouched.
- Intake #14 and accepted decision `0016-provider-neutral-graph-chat-acceptance` / DEC-029 add a
  DeepSeek Chat Completions graph-chat adapter without removing OpenAI Responses. DeepSeek translates
  native assistant/tool-result messages, disables thinking, sends no local metadata, normalizes
  usage and retains the same bounded redaction, Pydantic argument validation, read/propose-only tool
  set and draft review/apply governance. `GRAPH_CHAT_DEFAULT_PROVIDER=deepseek` is reversible.
- The UI now selects configured DeepSeek/OpenAI graph-chat providers and only enables a session when
  its provider is configured. The operator command is `verify-chat-provider`; `verify-openai` remains
  backward compatible. Ruff and all 168 backend tests pass; frontend lint/typecheck, 28 tests and the
  15-route build pass; 30 desktop/tablet/mobile E2E cases pass with six expected auth skips. API and
  frontend images were rebuilt and the runtime is healthy with 45 nodes/32 edges.
- Historical DeepSeek network note: the initial `deepseek-v4-pro` and isolated
  `deepseek-v4-flash` preflights timed out before an HTTP response even though DNS resolved. The
  later ready preflight and real draft-proposal proof above supersede that transient limitation.
  No secret, provider body or ID value was printed in either check.
- The third consecutive bounded blocker audit on 2026-07-21 passed runtime readiness and canonical
  graph invariants, then returned `CHAT_PROVIDER_UNAVAILABLE` from the secret-safe OpenAI preflight.
  The walkthrough and product-decision markers remain unchecked. No further ordered project work can
  proceed without a valid owner-managed key and Linh's acceptance, so the Codex goal is formally
  blocked; Gate C non-local operations and Discord were not started. Resume by mounting a valid key
  outside the repository, recreating only the API, running `python -m app.operations verify-openai`
  and `scripts/verify_graph_v2_acceptance.sh`, then completing the product-owner checklist. Harness
  detailed trace #19 records this blocker audit; drift entropy remains `0/100`.
- On 2026-07-21 the active `US-GV2-ACCEPT` story gained a narrow
  `docker-compose.openai-secret.example.yml` rotation overlay,
  `python -m app.operations verify-openai`, and
  `scripts/verify_graph_v2_acceptance.sh`. The preflight makes one minimal OpenAI Responses call
  with `store=false` and outputs only provider/model, typed status and ID/output-presence booleans;
  it never prints the credential, prompt, provider text, actual IDs or upstream body. Official
  OpenAI docs confirm the current Responses/internal strict-tool contract and `gpt-5.6-luna` model.
  The rebuilt API still receives upstream HTTP 401 with a request ID and the safe CLI returns exit
  2 / `CHAT_PROVIDER_UNAVAILABLE`.
- The Harness story now has a real executable verification command instead of prose. Full proof
  passes Ruff, all 165 backend tests, frontend lint/typecheck/build, 28 frontend tests, 30
  desktop/tablet/mobile Playwright cases and runtime graph checks, then intentionally fails on
  `GV2_OPENAI_ACCESS_PENDING`, `GV2_WALKTHROUGH_PENDING` and
  `GV2_PRODUCT_DECISION_PENDING`. It cannot complete until access is valid, every walkthrough item
  is checked, and Linh records exactly one accepting decision. Detailed trace #18 meets the
  high-risk tier and the current audit is `0/100`. No checklist box was self-approved.
- On 2026-07-21 high-risk story `US-INTAKE-RECEIPTS-IMPLEMENT`, intake #13 and detailed trace #17
  implemented the accepted DEC-028 boundary without starting Discord. Additive tables preserve one
  receipt per manual/API/platform occurrence and one URL/document item per observed source item;
  normalized-URL jobs and content-hash document workspaces remain canonical processing aggregates.
  Same occurrence/item replay converges under database uniqueness, different occurrences retain
  provenance without duplicate processing, and the compatibility `/ingestion/links` endpoint now
  dual-writes implicit receipts while preserving its response contract.
- Migration `a8b4c6d2e913` safely backfilled the main PostgreSQL runtime after a validated dump and
  exact restore drill. The pre-migration 27 links became 27 receipts/items with zero missing
  references and unchanged processing/review/research state. Two final three-viewport E2E proof
  runs plus the latest acceptance regression added 18 expected manual occurrences; current counts
  are 45 receipts / 45 items / 27 links,
  still with zero missing references, 8 research rows and 3 document workspaces. The validated
  pre-migration dump/list remain temporarily inside the database container under
  `/tmp/business-ai-pre-receipts.*`; they are ephemeral if the container is replaced.
- Revocable service accounts return the raw `research_svc_...` token only at creation, store its
  SHA-256 hash, and are limited to `intake:submit` / `intake:read-own` in one namespace. Receipt URL
  and document APIs enforce namespace isolation, bounded safe audit data and durable storage
  read-back before acknowledgement. A disposable real MinIO proof passed replay/conflict/orphan
  checks and was removed. Final proof passed Ruff, 163 backend tests, migration parity/backfill,
  receipt-spec verification, frontend lint/typecheck/build, 28 frontend tests, and 30 Playwright
  cases across desktop/tablet/mobile (six auth-only skips because local auth is disabled).
- Harness story `US-INTAKE-RECEIPTS-IMPLEMENT` completed with fresh proof; audit entropy is `5/100`
  only because `US-GV2-ACCEPT` still awaits product-owner/OpenAI chat acceptance. API/worker were
  rebuilt at the final image and the four-service runtime is healthy on API `18000` / frontend
  `13000`; readiness remains valid at 45 canonical nodes / 32 edges. Discord remains deferred until
  product acceptance and deployment-owned Gate C/D policies are recorded.
- On 2026-07-21 Gate C object-migration story `US-GATEC-OBJECT-MIGRATION`, intake #11 and decision
  `0014-copy-verify-object-migration`/DEC-027 completed the dry-run-first legacy local-object to MinIO
  path. Plan mode performs a read-only full inventory; execute requires `--confirm-copy-only`, then
  verifies local size/SHA-256, copies the same object name, reads and hashes the remote object,
  rechecks local bytes, and transactionally updates both references plus a bounded audit event one
  object at a time. Verify/repeat runs are resumable, and no command deletes local objects. Real
  disposable-MinIO proof passed and its container was removed. The main runtime was deliberately
  plan-only: 3 eligible objects / 2,822 bytes, zero missing/invalid objects; PostgreSQL still has 3
  plain keys and zero `attachment.object_migrated` audit events.
- On 2026-07-21 Gate C search projection story `US-GATEC-SEARCH-PROJECTIONS` implemented explicit
  Meilisearch and pgvector adapters without changing PostgreSQL ownership. Owner rebuild creates a
  validated approved-only staging index and atomically swaps it; pgvector stores real Mistral
  `mistral-embed` output in `vector(1024)` rows with HNSW cosine search. Selected providers fail
  visibly and ranked IDs are hydrated from current canonical rows. Migration `c5a8e2f4b901` is live
  on the preserved main volume under pgvector 0.8.5. Real proof passed repeat rebuild, injected stale
  pruning, lexical/semantic reads and canonical parity: 3 Meili documents, 3 vector documents / 9
  chunks, zero stale rows, one HNSW index, 8 canonical rows unchanged. The proof-only Meilisearch
  container/volume was removed; the internal-only digest-pinned profile remains available.
- Repository Harness `v0.1.17` is installed from `hoangnb24/repository-harness` commit `9cc306d2e06f34bac02237d20d14084553aefc64`. The install used merge mode, preserved the existing cross-agent instructions, appended one marked Harness block to `AGENTS.md`, created the lowercase `docs/` and `scripts/` Harness surfaces, bootstrapped schema 13, recorded intake #1, and passes drift audit with entropy `0/100`.
- On 2026-07-20 the existing Harness installation was bootstrapped idempotently, CLI `0.1.17` was confirmed, the active matrix was empty, and intake #2 recorded the tiny Harness/goal-alignment task. No application source or secret configuration was changed.
- On 2026-07-21 the high-risk `US-GV2-ACCEPT` story completed the engineering-assisted non-chat walkthrough. Workspace `de618dc2-6f87-4eff-a785-1665a229f9c4` reached `priority_review` at score 85.75 with 39 isolated nodes/33 edges through DeepSeek after a typed Mistral structured-graph failure; change set `d7dc15e4-bfb3-4c8c-a615-553c0359827d` applied 65 accepted mutations and excluded one rejected edge idempotently. Canonical readiness remains valid at 45 nodes/32 edges. This evidence does not mark product-owner acceptance.
- High-risk story `US-DOC-PROVIDER-RELIABILITY` is complete. Document-graph prompt v2 makes at most
  one recovery request to the same selected provider after a Pydantic `ValidationError`, sends only
  bounded issue categories/locations plus an invariant checklist, and never persists invalid output
  or silently substitutes a provider. Valid output makes one request; a second invalid response keeps
  the existing `AI_RESPONSE_INVALID` manual-retry path.
- Live Mistral workspace `c91507a7-d186-418c-9202-34220ec75dfd` completed on its first structured
  response at score 74.5 with 20 supported nodes, 14 edges and zero dangling endpoints. This proves
  prompt/schema v2 compatibility but not a live recovery event; invalid→valid and invalid→invalid
  recovery behavior is deterministic-test evidence.
- High-risk story `US-GATEC-MINIO` and decision `0008-routed-object-storage` are complete. New remote
  document objects use `minio://<configured-bucket>/...`; existing plain keys keep routing to the
  local named volume. Backend selection changes only new writes and never migrates/deletes objects.
  MinIO credentials are server-only and may come from managed secret files or local environment
  values; buckets are pre-provisioned by default, uploads enforce
  the existing size/hash contract with bounded spooling, downloads stream/close connections, and
  transient storage 5xx failures enter the bounded worker retry path.
- A disposable MinIO server on the internal Docker network passed put/open/delete without publishing
  a host port and was removed. Rebuilt local runtime workspace
  `32494694-4e0f-4b80-9086-3d78143672b5` passed upload/download with a legacy-local key. This does not
  claim managed production MinIO topology, encryption, backup or object migration.
- High-risk story `US-GATEC-NEO4J`, intake #9 and decision
  `0012-idempotent-neo4j-projection` are complete. The optional adapter atomically rebuilds validated
  relationship and hierarchy snapshots from PostgreSQL with composite identities, parameterized
  batches and stale pruning, then serves bounded query, branch, shortest-path and cluster reads
  without fallback. A disposable real server matched canonical projection counts across repeated
  rebuilds with zero duplicates and unchanged PostgreSQL counts. The profile is internal-only and
  digest-pinned; explicit rebuild freshness and production TLS/HA/capacity remain operational work.
- High-risk story `US-GATEC-OBSERVABILITY` and decision `0009-production-observability` are complete.
  Every API response has a validated/generated `X-Request-ID`; API and worker stdout use a strict
  JSON field allowlist; raw Uvicorn/httpx URL logs are suppressed; HTTP/provider/rate-limit/job
  telemetry uses bounded dimensions. `/metrics` is disabled by default and, when enabled, fails
  closed without an independently managed bearer secret. PostgreSQL `AuditEvent` remains the
  authoritative business audit trail; API metrics are process-local and the worker opens no
  unauthenticated scrape listener.
- High-risk story `US-GATEC-AUTH`, intake #7 and decision `0010-local-auth-rbac-and-secret-files`
  are complete. Local accounts use Argon2 hashes and random opaque sessions whose tokens are hashed
  at rest; browser mutations require the session-bound CSRF token. The API enforces
  `viewer < researcher < owner`, attributes durable audit/review actions to the authenticated actor,
  and provides owner user administration plus password-stdin operator provisioning.
- Trusted local mode remains the default. Staging/production fail configuration validation unless
  local auth, Secure cookies and a `__Host-` session-cookie name are enabled. Supported credentials
  prefer service-scoped `/run/secrets` files over environment values; the example Compose overlay
  validates. TLS, external secret rotation/manager, OIDC/MFA and tenant isolation remain external or
  follow-up work.
- High-risk story `US-GATEC-EXTRACTION`, intake #8, decision
  `0011-bounded-source-enrichment` and detailed trace #10 are complete. Optional Tesseract OCR is
  shared by URL and uploaded scanned PDFs with page/DPI/pixel/time/output bounds and provenance.
  Optional Browserless rendering runs only after direct article extraction reports
  `JS_RENDER_REQUIRED`, validates every browser subrequest, blocks heavy resources, publishes no
  host port and uses a digest-pinned image. Researchers can attach bounded timestamped transcripts
  only to unpublished public Reel/video submissions; the worker rehashes/reclassifies them, audit
  stores metadata only, queue APIs do not echo the body, and owner review remains mandatory.
- Migration head is `0b7d2e4f6a18`. Ruff and all 125 backend tests pass; web lint/type/build and 28
  unit tests pass; local E2E passes 30 cases across desktop/tablet/mobile with six auth-only skips.
  Actual image smoke proved Tesseract 5.5.0 `eng+vie` OCR and Browserless pressure/Playwright render.
  The optional browser container was removed and default OCR/browser flags were restored disabled.
- The acceptance run exposed dense document graph nodes compressed into one overlapping row. `DocumentGraphCanvas` now uses stable five-column row wrapping and expanded height; a 12-child regression proves three rows. Live desktop/mobile inspection, 24 frontend unit tests, 27 E2E cases, lint, typecheck and production build pass.
- Graph Intelligence v2 Phase 6 engineering is complete. The versioned 30-item release evaluation reports 1.00 priority/draft routing precision, 1.00 top-three pillar placement recall, 1.00 near-duplicate recall/precision and zero fixture schema failures. This is a deterministic regression set, not a claim of general-world provider accuracy.
- Document processing now sanitizes provider pillar labels against the canonical ontology, adds a deterministic top-three fallback, and records title-plus-dimension near-duplicate workspaces in `overlaps_with` for review. Neither fallback can merge or publish automatically.
- Server-enforced rollout flags cover the v2 master, document and chat surfaces. In-memory local rate controls protect uploads, analysis/retry, chat turns and graph apply with typed 429 responses. API responses expose timing headers and slow-request warnings omit bodies and secrets.
- `/api/v1/system/features` exposes non-secret rollout state; `/api/v1/system/readiness` and `python -m app.operations verify-graph` check the canonical root, hierarchy cycles, dangling parents/endpoints, self-loops, invalid confidence and duplicate node/edge/alias keys.
- `make evaluate-graph-v2` and `make verify-migrations` are repeatable release gates. SQLite upgrade/check/downgrade/upgrade and live PostgreSQL `alembic check` pass at `e9f5c2a7d104`. A separate PostgreSQL backup/restore drill restored matching counts and its temporary database/dump were removed.
- The rebuilt API/worker/frontend stack is healthy on ports `18000`/`13000`; readiness reports 45 valid canonical nodes and 32 valid edges after the acceptance change set, `/chat` returns 200, current post-restart logs contain no 500/traceback, and all unrelated `smart_exam_*` containers remain untouched. Product-owner acceptance and a real chat turn remain pending because the configured OpenAI credential is still rejected and maps to `503 CHAT_PROVIDER_UNAVAILABLE`.
- Graph Intelligence v2 Phase 5 is complete. PostgreSQL now stores local chat sessions/messages for graph, pillar, node, document, change-set and gap scopes; bounded context/history and cloud redaction feed a provider-neutral orchestration loop. The OpenAI Responses adapter uses strict function schemas, `store: false`, local state and request/model/usage provenance.
- Chat tools can perform bounded reads and propose nodes, edges, aliases and evidence attachments, but expose no publish/delete/SQL/filesystem/network capability. Proposals become `origin_type=chat` draft change sets and must pass the Phase 4 validation, approval and apply workflow. Unsourced proposals remain `evidence_pending`; provider/tool/loop failures are typed and persisted without canonical graph writes.
- `/chat` provides a bilingual responsive three-panel workspace for local sessions, brainstorm messages, scope context, tool activity and linked Knowledge Changes. Document, ontology-node and change-set pages can launch a scoped chat.
- Migration `e9f5c2a7d104` passed SQLite upgrade/downgrade/upgrade and is applied to PostgreSQL. The rebuilt stack is healthy on API `18000` and frontend `13000`; `/chat`, direct/proxied health and chat-session API return 200. The configured OpenAI credential currently receives HTTP 401 from the live Responses API, which the adapter maps to `CHAT_PROVIDER_UNAVAILABLE`; replace the runtime secret before real conversations.
- Graph Intelligence v2 Phase 4 is complete. Reviewable document workspaces create idempotent graph change sets; exact canonical labels/approved aliases map to evidence attachment, while bounded fuzzy matches remain visible candidates and never auto-merge. New nodes and semantic edges are proposed with source evidence previews and canonical parent placement.
- Change-set validation enforces evidence, approved endpoints/parents, controlled relations, confidence bounds, duplicate canonical nodes, self-loop prevention and proposed hierarchy cycle checks. Reviewers can edit supported fields, accept/reject individual mutations, approve/reject the full set, apply accepted changes transactionally/idempotently, and create an explicit compensating set that archives created nodes and supersedes created edges.
- `/graph/changes` and `/graph/changes/{id}` provide the bilingual review queue, source-to-canonical diff, similar candidate comparison, evidence-in-context, validation messages and lifecycle actions. A reviewable `/documents/{id}` workspace exposes the create-change-set action. Canonical graph writes remain reachable only through the approved apply service.
- The final API/worker/frontend images were rebuilt and recreated on ports `18000`/`13000`; PostgreSQL is healthy at migration `d7e3b9a1f604`, direct and proxied API health return 200, the new list/candidate APIs and graph-change page are healthy, worker startup is clean, and all unrelated `smart_exam_*` containers remained untouched.
- Graph Intelligence v2 Phase 3 is complete in code. The worker claims uploaded workspaces with leases, bounded retry and typed errors; extracts UTF-8 Markdown/text and bounded PDF text layers; persists content into the draft research item; evaluates paper fit through the selected provider; and keeps score, hard gates and routing server-owned.
- Papers scoring at least 60 produce a bounded isolated graph with server-created Document/Section structure plus typed AI semantic nodes and edges. Evidence excerpts must match the extracted source text; unmatched model evidence is retained only as explicit `evidence_pending`. Low-scoring and hard-gate inputs stop at review without a fabricated graph.
- `/api/v1/documents/{id}/evaluation` and `/graph` expose the evaluation and isolated graph, while analyze/retry endpoints enforce workspace state. `/documents/{id}` shows live status, seven score dimensions, provider/model provenance, limitations, a responsive hierarchy canvas and node-level evidence.
- The combined worker now processes URL intake and document jobs. OpenAI Responses structured calls explicitly send `store: false`; keys remain server-only and source text is treated as untrusted prompt data.
- Migration `d7e3b9a1f604` adds document job lifecycle fields plus isolated graph nodes/edges. Upgrade/downgrade/upgrade passed on temporary SQLite; the running PostgreSQL/Docker stack was not rebuilt in this session.
- Phase 3 verification passed: 67 backend tests, 19 frontend unit tests, Ruff, ESLint, TypeScript, Next.js production build, six mocked document Playwright cases across desktop/tablet/mobile, Compose validation and migration round trip.
- The paper-fit backend owns the exact seven-dimension weighted score and routing bands, hard-gate failures receive no misleading score, and the versioned gold set covers 10 core, 10 enabling, 5 tangential and 5 irrelevant papers.
- PDF, Markdown and plain-text uploads are bounded to a configurable 20 MB, validated by extension/content type and file signature/text safety, hashed with SHA-256 and stored behind a local `ObjectStorage` boundary outside the repository. Duplicate content returns a typed conflict and the redundant object is removed.
- Each accepted upload transactionally creates a draft research item, attachment metadata and one `DocumentGraphWorkspace`. `/api/v1/documents` supports upload/list/detail/download without exposing filesystem paths, `/documents` provides the bilingual upload/library UI, and Compose mounts a named object volume into API and worker.
- Graph Intelligence v2 Phase 2 is implemented in code. `/graph` now switches between the existing relationship network and a hierarchy projection without discarding the selected inspector node. Hierarchy mode resolves ontology roots, requests only one-hop branches with `root_node_id`, renders a stable layered D3 tree, supports breadcrumb/child navigation and exposes overview, children, evidence and provenance tabs. Root and breadcrumb ontology APIs complete the navigation contract.
- Phase 2 verification passed: 47 backend tests, 15 frontend unit tests, ESLint, TypeScript, Next.js production build and a mocked hierarchy Playwright scenario on desktop/tablet/mobile. The running Docker stack was not rebuilt in this session, so production-PostgreSQL runtime smoke remains a deployment step rather than a code blocker.
- Graph Intelligence v2 Phase 1 is implemented in the API. Migration `8c2d4e6f901a` adds canonical knowledge nodes/edges, aliases, evidence, change sets and mutations, then seeds one stable root plus eleven stable Business AI Agents pillars. `/api/v1/ontology` exposes tree/node/children/search/placement validation, and `/api/v1/graph?view=hierarchy` returns the approved parent-child projection while the existing relationship view remains the default.
- The additive graph contract now includes optional parent, child-count, lifecycle, provenance, alias, workspace and evidence fields. Placement validation rejects self-parenting and ancestor cycles. The 47-test backend suite passes and migration upgrade/downgrade/upgrade was exercised on a temporary SQLite database with 12 nodes, one root and eleven pillars.
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md` is accepted for phased implementation. DEC-018 locks the reversible defaults: eleven pillars, paper-fit threshold 60, PDF/Markdown/text up to 20 MB, `evidence_pending` brainstorm drafts, one display parent plus semantic parents, explicit change-set approval and a standalone ChatGPT-like `/chat` backed server-side by OpenAI Responses with `store: false`.
- `/graph` is healthy again after the 2026-07-17 rebuild exposed that the persistent `frontend_modules` named volume did not contain newly added `d3`, even though `package.json`, the lockfile, and rebuilt image did. Compose now checks `npm ls --depth=0` before starting Next.js and runs a bounded dependency sync only when the mounted volume is incomplete. The runtime contains `d3@7.9.0`; `/graph` compiles successfully and returns HTTP 200; TypeScript and all 12 frontend unit tests pass.
- The core Docker Compose stack was fully rebuilt and recreated on 2026-07-17 at 14:28 +07 using the current working tree. `database`, `api`, `worker`, and `frontend` are up on API port `18000` and frontend port `13000`; PostgreSQL remains healthy, direct API health, proxied health, and the frontend root return HTTP 200, and fresh startup logs are clean. The existing PostgreSQL volume was preserved, the optional Ollama bridge remains stopped, and unrelated `smart_exam_*` containers were not touched.
- The core Docker Compose stack was restarted on 2026-07-17 at 14:10 +07 without rebuilding or changing application code. `database`, `api`, `worker`, and `frontend` are up on API port `18000` and frontend port `13000`; direct API health, proxied health, and the frontend root return HTTP 200, PostgreSQL is healthy, and recent startup logs are clean. The optional Ollama bridge remains stopped and unrelated `smart_exam_*` containers were not touched.
- `Docs/Source Processing Pipeline.md` now provides the dedicated Vietnamese explanation of the `/ingestion` “Xử lý nguồn” path. It traces frontend batching, API URL normalization, PostgreSQL durable queueing, worker leasing, SSRF-safe bounded fetch, source adapters, normalized documents, content deduplication, structured AI classification, typed retry/failure paths, human review, and approved search/graph publication. Its Mermaid flowchart explicitly separates duplicates, retryable failures, partial success, rejection, and approval.
- The core Docker Compose stack was started again on 2026-07-17 at 09:39 +07 without rebuilding or changing application code. `database`, `api`, `worker`, and `frontend` are up on API port `18000` and frontend port `13000`; direct/proxied health and the frontend root return HTTP 200, PostgreSQL is healthy, and the fresh API/worker/frontend error scan is empty. The unrelated `smart_exam_*` containers were left running and untouched.
- The 2026-07-17 live DeepSeek audit verified `/models`, JSON-mode `LinkClassification`, queue/worker transitions and persisted classification for GitHub, generic article, arXiv paper and direct PDF sources. Facebook Reel intake returns the expected `partial_success`/`TRANSCRIPT_UNAVAILABLE`; private URLs return typed `INVALID_URL`; the worker processes the next valid job after a failure.
- A valid DataCite-managed arXiv DOI previously failed because DOI lookup was Crossref-only. Paper intake now falls back to bounded, redirect-revalidated DOI CSL content negotiation when Crossref returns 404; the original DOI succeeds and deduplicates against its existing arXiv record.
- PostgreSQL search previously returned HTTP 500 after approving a DeepSeek-classified item because SQL `DISTINCT` included JSON columns. Search/tag matching now uses relationship `EXISTS` predicates without row-level `DISTINCT`; the approved Goose research is returned by search and graph projection.
- Retry provider overrides are now schema-validated, removed legacy providers fall back to the configured default, and expected typed source/provider failures log a warning without a traceback. Unexpected internal failures still retain exception logging.
- The application AI `mock` provider was removed on 2026-07-17 from the backend factory/registry, intake schema, Compose/env defaults, frontend selector and current product docs. Mistral is active and configured in the running stack; invalid `provider=mock` intake requests return HTTP 422. Deterministic AI behavior now exists only as a test double.
- The core Docker Compose stack was rebuilt and started again on 2026-07-17 with `database`, `api`, `worker`, and `frontend` running on API port `18000` and frontend port `13000`. Direct API health, the frontend root, and the frontend API proxy all return HTTP 200; recent startup logs contain no error, exception, traceback, fatal, or failed entries.
- Local Docker runtime was rebuilt and restarted on 2026-07-15 at frontend `http://localhost:13000` and API `http://localhost:18000`; database, API, worker, and frontend are all running. Direct API health, frontend root, frontend API proxy, and API docs return HTTP 200.
- The optional `local-ai` Compose profile runs a bounded host-Ollama bridge. It exposes only tags/version/generate, rejects model pulls and arbitrary routes, and caps request size. The previously verified host model is not currently listed by `ollama list`, so Ollama is disabled in the selector until a configured model is reachable.
- AI provider discovery now reports Ollama reachability separately from configuration. The UI disables a configured-but-unreachable local provider; provider transport/rate/auth/invalid-response failures are persisted as typed ingestion errors without leaking upstream response details.
- Historical live provider probes passed for `mistral-large-latest`, `deepseek-v4-pro`, and local `qwen3.5:4b`. The current runtime uses Mistral because the host Ollama model list is empty. The Ollama adapter still sends the actual JSON schema and disables thinking so structured responses validate reliably when a model is available.
- Discord bot Gate D was brainstormed on 2026-07-15; no bot code was started. The recommended future design is a thin Gateway listener that creates one durable intake receipt per Discord message URL/attachment, while the existing Research System owns normalization, extraction, deduplication, classification, approval policy and projections.
- Before Discord implementation, the intake data model needs an occurrence/receipt layer separate from the URL-unique processing record. This preserves every Discord guild/channel/message provenance event while still deduplicating canonical content. PDF attachment upload/storage and text-layer extraction are also required for a true zero-step sender experience; arbitrary Facebook Reels remain conditional on lawful media access/transcript availability.
- The reported runtime/UI failures were audited with real browser console/network checks, interaction tests and live mixed-source submissions. The current stack is running on ports 18000/13000 and is accepted as stable for the implemented MVP boundaries.
- The frontend now uses an accessible deep-ocean visual system across dashboard, intake, research list/detail/editor, search, graph, gaps, collector and training: sticky navy topbar, teal primary, indigo accent, pale blue-gray canvas, cool surfaces and self-hosted Inter. Desktop, tablet and mobile navigation preserve access to every route; the intake queue is bounded and scrollable on desktop.
- Base Compose no longer forwards host `NEXT_PUBLIC_API_URL`; local browsers always use relative `/api/v1` through the frontend proxy. This prevents stale `localhost:8000` settings from bypassing the container API and causing CORS failures.
- A second Compose project was started from empty volumes, migrated automatically to `73f6a8c1d2e0`, processed `https://example.com/` from `pending` to `completed`, and was then removed with its test volumes.
- Graph API now returns a validated `{nodes, edges, meta}` contract with default/hard limits, filters, search, 1-2 hop traversal and neighbor expansion. `GRAPH_DATA_PROVIDER=postgres` is the default; `mock` is contract-valid and `neo4j` fails explicitly until its adapter is implemented.
- URL intake now dispatches through normalized GitHub, article, public Facebook, scientific-paper and direct-PDF adapters. Useful metadata-only results are `partial_success`; private/paywalled/JS-only/scanned content remains an explicit limitation rather than fake success.
- The graph UI is split into API/hooks/mapper/theme/layout/canvas/toolbar/filter/legend/details/evidence modules. Cytoscape is created once, preserves positions, resizes via `ResizeObserver`, and cleans up listeners/instance on unmount.
- Research uses the existing lifecycle: `approved` is the published/searchable/graph-visible state. The UI now has all/review/published/rejected tabs, and rejected research can be resubmitted.

- AI provider registry now includes Mistral (`mistral-large-latest` by default) through strict JSON Schema chat completions; configure it with `MISTRAL_API_KEY` and optional `MISTRAL_MODEL`.
- URL intake is asynchronous: API submissions enter a durable PostgreSQL queue and the Compose `worker` processes them with leases, exponential retry and dead-letter/manual retry.
- Latest migration is `e9f5c2a7d104`; API submit returns HTTP 202 for newly queued links and HTTP 200 for an existing URL.
- FastAPI nằm tại `apps/api/`, Next.js nằm tại `apps/web/`; mọi deployable app mới tiếp tục đặt dưới `apps/`.
- Root chỉ giữ tài liệu/quy ước toàn repo và các entrypoint vận hành như `README.md`, `Makefile`, `docker-compose.yml`.
- PostgreSQL là database trong Docker; SQLite được dùng cho local test nhanh.
- Migrations: `22b42804e1f5`, `b4519e47487f`, `5d7a8c91e2f0` và `9f3c2a7b1d44`.
- App chạy bằng `docker compose up --build` hoặc các lệnh trong `README.md`.
- Test chạy bằng `make test`; lint bằng `make lint`; frontend build bằng `make build`.
- Docker smoke instance hiện đang chạy ở frontend `http://localhost:13000` và API `http://localhost:18000` vì port 8000 đang bị project khác chiếm.
- Gap workspace nằm tại `/gaps`; API detector/workflow nằm dưới `/api/v1/gaps`, với compatibility read endpoint `/api/v1/graph/gaps`.
- Completion plan nằm tại `Docs/Research System Completion Plan.md`; link intake UI ở `/ingestion`, API ở `/api/v1/ingestion/links`.
- AI registry hỗ trợ Ollama, OpenAI, DeepSeek, Gemini, OpenRouter và Mistral; không có in-process fake fallback, và UI chỉ cho chọn provider đã cấu hình/khả dụng.

## Completed

- [x] Completed Gate C Meilisearch/pgvector projections with atomic repeat rebuild, real semantic
  embeddings, canonical hydration, stale pruning, live PostgreSQL migration and real service proof.
- [x] Completed the Gate C MinIO attachment adapter with reversible routed keys, legacy local access,
  safe configuration/failure handling, live isolated object round trip and full regression proof.
- [x] Completed bounded same-provider structured document-graph recovery with strict schema/invariant
  validation, safe provider telemetry, live Mistral compatibility and full backend/browser regression.
- [x] Install Repository Harness `v0.1.17` in merge mode, preserve and back up the existing `AGENTS.md`, bootstrap the local ignored Harness database to schema 13, record the tiny installation intake, and verify CLI contract, marker integrity, ignore rules, idempotent bootstrap and entropy `0/100`.
- [x] Completed Graph Intelligence v2 Phase 6 engineering: gold evaluation, production placement/duplicate safeguards, feature flags, rate/timing controls, graph invariants, migration parity, backup/restore drill, runbook, acceptance checklist and rebuilt full-stack verification.
- [x] Completed Graph Intelligence v2 Phase 5 graph-aware chat: local session/message persistence, six scopes, strict bounded read/propose tools, OpenAI Responses adapter with `store: false` and redaction, governed change-set proposals, bilingual responsive UI and rebuilt runtime verification.
- [x] Completed Graph Intelligence v2 Phase 3 document workflow: leased/retryable worker stages, bounded PDF/Markdown/text extraction, provider-neutral paper evaluation, deterministic routing, isolated nodes/edges, verbatim evidence validation, analysis/graph APIs and responsive `/documents/{id}` UI.
- [x] Implemented the Graph Intelligence v2 Phase 3 scoring/upload foundation: deterministic paper-fit hard gates and routing, a versioned 30-item gold set, bounded PDF/Markdown/text storage, draft research/workspace persistence, document APIs, bilingual `/documents` UI and responsive upload E2E coverage.
- [x] Implemented Graph Intelligence v2 Phase 2 hierarchy UX: ontology roots/breadcrumb APIs, lazy one-hop branch loading, layered D3 tree layout, relationship/hierarchy switcher, selection preservation, breadcrumb/child navigation, four detail tabs and responsive desktop/tablet/mobile coverage.
- [x] Accepted Graph Intelligence v2 defaults and implemented Phase 1: additive ontology/evidence/change-set schema, deterministic root plus eleven pillars, hierarchy cycle validation, ontology read APIs, backward-compatible graph hierarchy mode, tests and migration round trip.
- [x] Replaced Cytoscape.js with D3.js for Knowledge Graph visualization: force-directed layout, custom node shapes (circle/rect/diamond), hover effects, zoom controls, drag interaction, and responsive design. ESLint, TypeScript, 12 Vitest tests and Next.js production build pass.
- [x] Optimized Knowledge Graph UI: reduced node size (36px→26px), increased font (10px→11px), added hover/selected effects, zoom controls, collapsible filters/legend, improved layout parameters, and better visual hierarchy.
- [x] Added dedicated Vietnamese source-processing pipeline document with a complete Mermaid flowchart, processing/review state machines, adapter matrix, retry/error semantics, and implementation code map.
- [x] Live-audited DeepSeek and the complete source-to-review-to-publish/search/graph path; fixed registry-neutral DOI fallback and PostgreSQL JSON search, hardened retry/log handling, and passed the full backend/frontend/browser/runtime gate.
- [x] Reworked the full UI from warm red-orange to the deep-ocean navy/teal/indigo palette, including graph and app icon; verified all core text/action contrast ratios at WCAG AA.
- [x] Added the bounded optional host-Ollama bridge and verified the existing `qwen3.5:4b` model from the API container without downloading any image or model.
- [x] Fixed Ollama structured-output handling (`format` schema plus thinking disabled), added provider reachability and typed upstream error mapping, and covered them with regression tests.
- [x] Live-tested GitHub with DeepSeek, a generic article with local Ollama, a direct text-layer PDF with Mistral, and a Facebook Reel with Mistral. The first three completed and classified; the Reel safely returned `partial_success` with `TRANSCRIPT_UNAVAILABLE` because no public transcript was available.
- [x] Rebuilt the URL pipeline as normalize/detect/validate/fetch/extract/clean/analyze/persist/display with observable stages, typed errors, bounded redirects/bytes/pages/timeouts/retries and job-ID logging.
- [x] Implemented GitHub repo/file/issue/PR, Facebook post/Reel/watch metadata, arXiv/DOI/Semantic Scholar/publisher metadata, direct PDF text-layer and generic article extraction behind one document contract.
- [x] Separated processing status from review status, added partial-success limitations and safe content-hash deduplication, and migrated existing records.
- [x] Rebuilt the complete frontend in the Smart Exam design language while preserving multi-URL intake, row-level actions, research workflows, graph interaction and bilingual content.
- [x] Self-hosted Inter, replaced the sidebar with responsive topbar/pill navigation, added the reference-style dashboard hero/quick-start/metrics and unified all panels/forms/tables/status states.
- [x] Extended Playwright coverage to all eight primary routes and desktop/tablet/mobile viewports, including exact visual-token, untranslated-status and horizontal-overflow assertions.
- [x] Added URL/adapter/integration tests, intake state component tests and Playwright desktop/tablet interaction, console/network and overflow coverage.

- [x] Typed graph node/edge/meta schemas with duplicate, dangling-edge, self-loop and metadata count validation.
- [x] Bounded graph query/filter/search/neighbors endpoints and deterministic stable projection IDs.
- [x] Source adapter registry with URL detection/canonicalization and normalized source schema.
- [x] Practical GitHub and Article adapters; safe Facebook Reel/PDF pending states.
- [x] Refactored responsive Cytoscape workspace with loading/empty/error/retry/truncation states, filters, selection, details, evidence, hide/expand, fit/reset/re-layout.
- [x] Research review tabs and reject/resubmit API/UI workflow.
- [x] Dashboard gap wording and system flow corrected; graph/source environment and README documentation updated.
- [x] Frontend Vitest/Testing Library foundation and graph lifecycle/state/dedup tests.

- [x] Fixed intake resubmission: failed/dead-letter URLs now requeue with the newly selected provider instead of silently returning the stale submission; UI shows queued/existing feedback.
- [x] Mistral provider adapter, strict structured output validation, environment/Compose wiring, registry/UI discovery and request-shape tests.
- [x] Gate C worker foundation: durable intake queue, separate worker service, retry/backoff, lease recovery, dead-letter state, manual retry and polling UI.
- [x] Phase 0 MVP specification và acceptance criteria.
- [x] Phase 1 FastAPI/Next.js/PostgreSQL/Docker foundation, migration, CORS, health và error format.
- [x] Phase 2 Research CRUD, lifecycle, versioning, comments, tags, relations, attachment metadata và UI editor/library.
- [x] Phase 3 approved-only search, filters, suggestions, related research và semantic API fallback.
- [x] Phase 4 rebuildable graph projection, node/ego/path/stats APIs và graph UI.
- [x] Phase 5 multi-provider AI adapters, provenance, embeddings, suggestion accept/reject UI; runtime fake provider was removed on 2026-07-17.
- [x] Phase 6 RSS source/run/evaluation/dedup/review/auto-ingest workflow và UI.
- [x] Phase 7 Training Data Hub events/examples/governance/datasets/JSONL export và UI.
- [x] Seed data, backend tests, frontend lint/type/build, dependency audit và Docker smoke test.
- [x] Refactor repository thành monorepo `apps/api` + `apps/web`, cập nhật Compose/Make/README và tài liệu kiến trúc.
- [x] Phase 8 foundation: persisted low-coverage gaps, prioritize/assign/dismiss/snooze, deep-research draft, human approval gate và gap workspace UI.
- [x] Docker port override cho phép cấu hình CORS; frontend `.next` dùng named volume để không tạo root-owned build artifacts trên host.
- [x] Completion Gate A: source-neutral URL intake, safe public URL validation, extraction, content-hash dedup, structured classification, review/publish và provider registry.
- [x] Typed graph ontology projection, graph clusters/stats và Cytoscape.js interactive canvas.
- [x] Persistent EN/VI locale switcher cho toàn bộ application UI, gồm shell, dashboard, link intake, graph, research, search, collector, gaps và training workflows.

## In Progress

- [ ] Gate C remaining deployment work: separately authorized production MinIO provisioning and
  execution of the verified copy-only migration,
  TLS/egress policy, external secret rotation and telemetry retention/alerts. Auth/RBAC,
  file-mounted secrets, background jobs/retry, practical source extraction, bounded OCR/browser,
  routed MinIO storage and production-safe application observability are complete.
- [ ] Discord adapter chỉ bắt đầu sau khi Graph v2 acceptance và các deployment-owned Gate C
  operations hoàn tất; cả ba projection adapters Meilisearch/pgvector/Neo4j đã hoàn thành. Receipt
  contract, additive schema/API/backfill và scoped service-account boundary đã hoàn thành; target
  guild/channel/media/token/rate/status policy vẫn cần owner/operator chấp nhận.

## Next Best Actions

1. Inspect the corrected hierarchy at `http://localhost:13000/graph` and review change set
   `5759af2f-4685-4cfa-b360-39d7981a1fa4`, then complete the walkthrough and rollout decision in
   `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`; only the product owner marks it.
2. Treat OpenAI credential replacement as optional switchback work. If selected later, mount the key
   from an owner-only file and run the secret-safe `verify-openai` preflight before changing default.
3. Provision production MinIO TLS/encryption/backup, take the required backup, and separately
   authorize `migrate-objects --mode execute --confirm-copy-only`; run verify before considering any
   later local-volume retirement. The application provides no deletion command.
4. Collect real provider/job/HTTP time series through the new protected telemetry surfaces and set
   deployment-owned retention, dashboards and alert thresholds; token cost remains provider-specific.
5. After product acceptance, record target-environment owners/evidence for remaining Gate C
   operations and Gate D guild/channel/media/token/rate/status policy. Only then start Discord.

## Decisions Locked

- PostgreSQL là source of truth; search và graph là projection rebuild được.
- API giữ prefix `/api/v1`.
- Mistral là configured default; Ollama và các cloud provider khác là adapters tùy cấu hình; application không có fake AI fallback.
- AI không tự ghi đè human fields.
- Training example phải qua PII, policy và provenance checks.
- RSS là collector duy nhất trong MVP.
- Deployable application code nằm dưới `apps/`; chỉ tạo `packages/` khi có code thực sự dùng chung giữa nhiều app.
- Gap detector v1 dùng approved concept coverage và lưu projection có thể rebuild; deep-research report luôn bắt đầu ở draft và phải qua human review.
- Discord không chứa business logic; nó chỉ gọi source-neutral intake API với source metadata/idempotency key.
- Provider output luôn qua structured schema + Pydantic validation; API keys lấy từ managed secret files hoặc environment local và không trả qua API.

## Do Not Touch

- Không xóa/overwrite brainstorm, architecture và implementation plan.
- Không chạy `npm audit fix --force`; PostCSS đã được override lên bản vá an toàn mà không đổi Next.js.
- Không dừng các container `smart_exam_*`; chúng thuộc project khác.
- Không lưu secrets/PII trong repo hoặc AI logs.

## Known Issues

- A fresh `npm audit --omit=dev` on 2026-07-25 reports three high-severity production dependency
  advisories in direct `next` and transitive `postcss`/`sharp`. No forced or breaking dependency
  upgrade was attempted during the scoped graph correction; assess patched compatible versions in a
  separate maintenance intake.
- The migration command is ready and the main read-only plan is clean, but managed production MinIO
  topology, credentials, backup and the explicit execute authorization are external. The current
  main database remains intentionally unchanged with three plain local keys and no migration audit.
- The configured OpenAI secret is present but the live Responses API returned HTTP 401 during Phase
  5 smoke verification. The adapter safely maps this to `CHAT_PROVIDER_UNAVAILABLE`; OpenAI
  switchback requires a valid replacement secret, but current `/chat` acceptance uses the verified
  DeepSeek default. No secret value was printed or logged.
- A new application-path recheck in session `651f826e-24d0-4341-bbdf-5aa3c5121056` still returned
  typed HTTP 503 with no provider response/request ID or change set. This is OpenAI-only historical
  evidence; replace that credential outside source control before any later switchback.
- During the first 2026-07-21 acceptance fixture, Mistral returned valid paper-fit output but invalid
  structured document-graph analysis. This is now hardened with one bounded same-provider recovery;
  terminal failure remains visible as `AI_RESPONSE_INVALID`, and manual retry may explicitly select a
  different provider. There is deliberately no automatic cross-provider fallback.
- Phase 5 chat is turn-based with a visible thinking state; token streaming/SSE and voice/realtime are intentionally deferred. Local summarization is deterministic and user-triggered.
- Uploaded documents require the worker and a configured/reachable selected AI provider to complete evaluation. Scanned PDFs use optional bounded OCR when enabled; disabled/unavailable/low-output OCR stops safely with a typed limitation.
- Local Ollama requires the host service to remain available. The current Linux Compose bridge binds on the Docker bridge address and is an explicitly optional local-development profile, not a production inference gateway.
- Arbitrary Facebook Reels may expose metadata but no lawful public transcript. Researchers can supply a bounded timestamped transcript they already possess, but the pipeline never logs in, downloads media, bypasses region/access controls or auto-publishes it.
- `GRAPH_DATA_PROVIDER=neo4j` is a real optional projection. It fails with typed HTTP 503 when
  unconfigured/unavailable, never returns fake data or silently falls back, and requires an explicit
  owner rebuild after canonical changes until a durable outbox is separately implemented.
- OCR and Browserless are disabled by default. When enabled they remain page/pixel/time/output/request bounded; private/region-locked Facebook and paywalled full text are never bypassed. Failures retain typed partial results.
- Scientific-paper URLs normalize metadata and expose available PDF URLs, but do not automatically download publisher/arXiv full text; direct PDF URLs use the bounded text-layer extractor.
- Root `PLAN.md` không tồn tại; implementation dùng file kế hoạch được handoff xác nhận là `Docs/Research System Implementation Plan.md`.
- Pytest báo một deprecation warning từ FastAPI/Starlette TestClient về package `httpx`; không ảnh hưởng test result.
- Port mặc định API 8000 đang bị `smart_exam_backend` ngoài project chiếm trong máy hiện tại; Compose hỗ trợ `API_PORT`/`FRONTEND_PORT` override.
- Production MinIO topology/migration, Redis transport and remaining deployment hardening are still
  open. Meilisearch, pgvector and Neo4j projections are implemented and fail visibly when selected
  without their optional services/credentials. Local auth/RBAC and file-mounted secret support are
  complete, but TLS,
  OIDC/MFA, external secret rotation/manager and tenant isolation remain deployment/follow-up work.
  Local storage remains the current write backend; scraper retention and alerts remain operational
  responsibilities.
- Phase 8 chưa có failed-search/trend signal, weekly digest hoặc autonomous deep-research agent.
- Browserless uses a large digest-pinned image. Pulling it required pruning 6.582 GB of unused,
  rebuildable Docker build cache after an initial no-space failure; no images, volumes or product
  data were deleted. Root storage has about 2.6 GB free and should be expanded/reclaimed before
  another large image upgrade.
- Locale stores UI preference in browser local storage; research content and existing user-entered data remain in their original language by design.
- The host `apps/api/.venv/bin/pytest` launcher contains a stale pre-monorepo shebang. Use
  `uv run --frozen python -m pytest` (verified working) or rebuild the host virtualenv before invoking
  that launcher directly.

## Verification

- 2026-07-25 board-first hierarchy correction: intake #16, human correction intervention #2 and
  story `US-GRAPH-BOARD-DRILLDOWN` hold the proof. Initial live view contains one root plus eleven
  collapsed boards; single-clicking `Data, Knowledge & Memory` opens its 33 direct nodes in three
  readable display columns with root/board breadcrumb and no sibling boards. Frontend
  lint/typecheck, 32 tests, the 15-route production build and 15 Playwright cases across
  desktop/tablet/mobile pass. The rebuilt frontend returns HTTP 200, runtime remains ready at 45
  nodes / 32 edges, and live Chrome reports no console/page errors.
- 2026-07-25 live DeepSeek graph-chat proof: API-container TCP/443 is reachable and
  `verify-chat-provider` returns `ready` for `deepseek-v4-pro` with allowlisted presence booleans
  only. Real graph-scoped turns exercised bounded search/context tools and stopped safely at
  `CHAT_TOOL_LOOP_LIMIT` when broad. A clean document-scoped turn used retrieved source evidence
  through `create_change_set` and `propose_node`, creating review change set
  `5759af2f-4685-4cfa-b360-39d7981a1fa4`. It has one evidence-supported valid mutation, zero errors
  or warnings and no canonical apply.
- 2026-07-25 owner-aligned hierarchy: intake #15 and implemented story `US-GRAPH-HIERARCHY` hold
  the proof. Ruff and 41 focused paper-fit/document/ontology/change/chat backend tests pass with only
  the known Starlette/httpx warning. Frontend lint/typecheck, all 29 tests and the 15-route
  production build pass; 15 upload/document-graph/hierarchy/chat/change-review E2E cases pass across
  desktop/tablet/mobile. Live Chrome proof starts with 12 horizontal hierarchy cards, focuses
  `Data, Knowledge & Memory` into a bounded 17-card root/pillar/descendant branch without siblings
  or console errors, and keeps truncation visible. Rebuilt API/frontend plus preserved
  database/worker return HTTP 200 and ready at 45 nodes / 32 edges; startup logs are clean and
  `smart_exam_*` was untouched.
- 2026-07-25 runtime restart: base Compose configuration validates; the existing database, API,
  worker and frontend containers started successfully with `API_PORT=18000`,
  `FRONTEND_PORT=13000` and local CORS set to the frontend. Direct API health, frontend root and
  proxied health return HTTP 200; feature flags are enabled; readiness is `ready` with a valid
  45-node / 32-edge graph; `alembic current` reports `a8b4c6d2e913 (head)` and
  `python -m app.operations verify-graph` passes. The fresh API/worker/frontend log scan found no
  traceback, exception, fatal or HTTP 500 entry, and `smart_exam_*` was untouched.
- 2026-07-21 Graph v2 acceptance preflight hardening: official OpenAI docs/API spec confirm the
  Responses tool shape, `store=false` and `gpt-5.6-luna`; focused operator/chat tests pass and the
  complete regression reports 165 backend tests, 28 frontend tests and 30 Playwright passes with
  six expected local-auth skips. The API image was rebuilt/recreated; readiness remains valid at 45
  nodes/32 edges and current logs have no traceback/fatal/HTTP 500. The safe provider preflight
  returns typed exit 2 because upstream still returns HTTP 401. The executable acceptance verifier
  reaches and reports all three remaining gates without changing the checklist.
- 2026-07-21 intake receipt specification: Harness intake #12, decision 0015/DEC-028, completed
  high-risk story `US-INTAKE-RECEIPTS-SPEC` and detailed trace #15 hold docs-only proof.
  `bash scripts/verify_intake_receipt_spec.sh` returns `INTAKE_RECEIPT_SPEC_OK`; it checks the
  domain/API/idempotency/document/auth/audit/concurrency/migration/Gate D contract, replay and
  repeated-occurrence scenarios, cross-document links, balanced Markdown fences and scoped diff
  hygiene. Harness story and decision verification/completion pass; final audit entropy is `5/100`
  only because product-owner story `US-GV2-ACCEPT` remains open. No application/runtime
  implementation is claimed.
- 2026-07-21 Gate C object migration: Harness intake #11, decision 0014/DEC-027, completed story
  `US-GATEC-OBJECT-MIGRATION` and detailed trace #14 hold the proof. Ruff, all 150 backend tests,
  SQLite migration parity, base Compose validation and `git diff --check` pass. A disposable
  internal-only MinIO tmpfs server proved plan, execute, remote read-back/SHA verification, audit,
  local retention, repeat no-op and verify (`1` object / `45` bytes); it was removed. The rebuilt
  API/worker runtime is ready at 45 nodes/32 edges, direct/proxied health pass, six document
  Playwright cases pass across desktop/tablet/mobile and current service logs are clean. The main
  plan reports 3 eligible local objects / 2,822 bytes with zero invalid/missing; database inspection
  confirms 3 plain keys, 0 remote keys and 0 migration audit events, so production execution is not
  claimed. A safe OpenAI application-path recheck still returned typed 503
  `CHAT_PROVIDER_UNAVAILABLE` without printing the credential or request content.
- 2026-07-21 Gate C search projections: Harness intake #10, decision 0013/DEC-026, completed story
  `US-GATEC-SEARCH-PROJECTIONS` and detailed trace #13 hold the proof. Ruff and all 141 backend tests,
  migration parity at `c5a8e2f4b901`, frontend ESLint/TypeScript/28 tests, 30 Playwright cases,
  base/search/managed-secret Compose config and live secret-overlay startup pass. A pre-recreate
  PostgreSQL logical backup validated; the preserved main volume is healthy on pgvector 0.8.5 with
  8 canonical / 3 approved research rows. Disposable real Meilisearch plus real Mistral embedding
  proof passed three rebuilds, injected stale pruning, lexical/semantic reads, 3/3 document parity,
  9 chunks at 1024 dimensions and one HNSW index. The temporary dump, Meilisearch containers and
  rebuildable proof volumes were removed; main API/worker/database/frontend remain healthy on
  18000/13000 and `smart_exam_*` was untouched. Harness audit entropy remains `5/100` only because
  external product-owner `US-GV2-ACCEPT` is still unverified.
- 2026-07-21 Gate C Neo4j projection: completed Harness story `US-GATEC-NEO4J`, intake #9,
  decision 0012/DEC-025 and detailed trace #12 hold the proof. Ruff and all 130 backend tests pass;
  base/profile Compose and API build pass; the rebuilt main API/worker are healthy and readiness is
  valid at 45 nodes/32 edges. A disposable real Neo4j server passed two-view atomic repeat rebuild,
  injected stale-row pruning, two composite constraints, zero duplicates, unchanged canonical
  counts, relationship parity 78/73, hierarchy parity 45/44, bounded branch/search/path and five
  clusters. Wrong credentials returned typed 503 without leakage, and proof-log scanning found no
  Cypher, URI or credential marker. The six-worker Playwright run exposed five dev-server timeout
  flakes; the complete serial rerun passed 30 cases with six auth-only skips.
- 2026-07-21 Gate C source enrichment: completed Harness story `US-GATEC-EXTRACTION`, intake #8,
  decision 0011 and detailed trace #10 hold the proof. Ruff and 125 backend tests pass; migration
  `0b7d2e4f6a18` passes upgrade/model-parity/downgrade/upgrade; web lint/type/build and 28 tests pass;
  30 local Playwright cases pass with six enabled-auth-only skips. API/worker/frontend images build.
  Actual image smoke reads a generated scanned PDF using Tesseract 5.5.0 with `eng+vie`; disposable
  Browserless returns pressure 200 and renders a public page through Playwright while remaining
  internal-only and up after the probe. Default runtime is restored with both features disabled and
  readiness valid at 45 nodes/32 edges. The temporary browser container was removed; `smart_exam_*`
  was untouched.
- 2026-07-21 Gate C auth/RBAC/secrets: completed Harness story `US-GATEC-AUTH`, decision 0010 and
  detailed trace #9 hold the proof. Ruff and all 118 backend tests pass; frontend ESLint, TypeScript,
  optimized build and 15 Vitest files/26 tests pass. Migration head `f3a6c8d1e204` passed empty
  upgrade/model parity/downgrade/upgrade. Existing local mode passed 27 Playwright cases; enabled
  auth passed six owner/viewer login/logout/role-visibility cases across desktop/tablet/mobile. Images
  and both Compose configurations validate. Runtime is restored to local-disabled and ready at 45
  nodes/32 edges; temporary identities, sessions and proof audit rows were removed.
- 2026-07-21 Gate C observability: Harness intake #6, decision `0009-production-observability` and
  completed story `US-GATEC-OBSERVABILITY` hold the proof. Ruff and 104 backend tests pass; 27
  Playwright desktop/tablet/mobile cases pass; API/worker images build. A temporary enabled runtime
  returned 401 without the scraper bearer and 200 with the integration-only value, exposed only
  route-template metrics and emitted correlated JSON logs. The runtime was restored to the disabled
  default: health 200, `/metrics` 404 and readiness valid at 45 nodes/32 edges. Detailed Harness
  trace #7 meets the high-risk 3/3 tier; audit entropy is `5/100` only because product-owner story
  `US-GV2-ACCEPT` remains intentionally unverified.
- 2026-07-21 Gate C MinIO adapter: MinIO SDK 7.2.20 is locked; final API/worker images build; Ruff and
  all 96 backend tests pass with only the known Starlette/httpx warning; all 27 Playwright cases pass.
  A no-host-port disposable MinIO tmpfs container passed 32-byte put/streamed-open/delete and was
  removed. The rebuilt local runtime passed upload/download with a plain local key; direct/proxied
  health and graph readiness are valid. Harness intake #5, decision `0008-routed-object-storage` and
  completed story `US-GATEC-MINIO` hold the proof.
- 2026-07-21 provider reliability: Ruff passes across API app/tests; all 88 backend tests pass with
  only the known Starlette/httpx warning; 27 Playwright desktop/tablet/mobile cases pass; Compose
  config and focused `git diff --check` pass; API/worker were rebuilt and restarted on 18000; direct
  readiness is valid at 45 canonical nodes/32 edges. The live Mistral document completed at score
  74.5 with 20 supported nodes/14 edges and no dangling endpoint. Recent API/worker/frontend logs
  contain no traceback, exception, fatal or HTTP 500 entry. Harness intake #4 and completed story
  `US-DOC-PROVIDER-RELIABILITY` hold the proof.
- 2026-07-21 engineering-assisted acceptance: direct/proxied health pass; PostgreSQL remains at `e9f5c2a7d104`; readiness is valid at 45 nodes/32 edges; the real upload/evaluation/isolated-graph/evidence/change-review/apply/history flow completed; rejected mutation absence and idempotent reapply were verified. Ruff and 26 focused backend tests pass. Frontend ESLint, TypeScript, 24 Vitest tests, the 15-route production build and all 27 Playwright desktop/tablet/mobile cases pass. Current post-restart API/worker/frontend logs contain no traceback, exception, fatal or HTTP 500 entry. Harness detailed trace #3 meets the high-risk tier; audit entropy is `5/100` only because `US-GV2-ACCEPT` remains unverified. The real OpenAI turn persists a safe assistant `CHAT_PROVIDER_UNAVAILABLE` and no change set, so final chat/product-owner acceptance is not claimed.
- Phase 6 engineering and rebuilt runtime: gold evaluation passes 30 fixtures at 1.00 routing precision, top-three placement recall, duplicate recall and duplicate precision with zero fixture schema failures; Ruff and `git diff --check` pass; 85 backend tests pass with only the known Starlette/httpx warning; frontend ESLint, 23 Vitest tests and Next.js build pass; all 27 Playwright cases pass on desktop/tablet/mobile. SQLite migration parity and live PostgreSQL `alembic check` pass at `e9f5c2a7d104`. A PostgreSQL dump/restore drill matched `5,12,0` research/node/chat counts and cleaned its temporary assets. Rebuilt readiness is `ready`, graph invariants are valid, timing headers are present, startup logs are clean and `smart_exam_*` remained untouched.
- Phase 5 and rebuilt runtime: Ruff and `git diff --check` pass; 78 backend tests pass with only the known Starlette/httpx warning; frontend ESLint, 23 Vitest tests and Next.js production build pass; all 27 Playwright cases pass across desktop/tablet/mobile. Migration `e9f5c2a7d104` passed SQLite upgrade/downgrade/upgrade and is live at PostgreSQL head. Rebuilt API/worker/frontend services are up, direct/proxied health, `/chat` and `/api/v1/chat/sessions` return 200, logs are clean, and `smart_exam_*` remained untouched. A minimal live OpenAI adapter probe reached Responses but the current credential returned 401 and was safely typed as unavailable.
- Phase 4 and rebuilt runtime: Ruff passes; 71 backend tests pass in the Compose API environment with only the known Starlette/httpx warning; frontend ESLint, 22 Vitest tests and Next.js production build pass; all 24 Playwright cases pass across desktop/tablet/mobile. `git diff --check` passes. Rebuilt API/worker/frontend services are up, PostgreSQL is healthy at `d7e3b9a1f604`, `/api/v1/health` works direct and through the frontend proxy, `/api/v1/graph/change-sets`, ontology candidate lookup and `/graph/changes` are healthy, and `smart_exam_*` was not touched.
- Phase 3 document workflow: Ruff passes; 67 backend tests pass with the existing Starlette/httpx warning; frontend ESLint, TypeScript, 19 Vitest tests and Next.js production build pass; migration `d7e3b9a1f604` passes upgrade/downgrade/upgrade on temporary SQLite; mocked upload plus processed evaluation/graph/evidence flows pass six Playwright cases across desktop/tablet/mobile; Compose config passes. The Docker runtime was not rebuilt.
- Phase 3 scoring/upload foundation: Ruff passes; 62 backend tests pass with the existing Starlette/httpx warning; frontend ESLint, TypeScript, 17 Vitest tests and the Next.js production build pass; migration `a4f1c7d9e205` completes upgrade/downgrade/upgrade on temporary SQLite; mocked document upload passes Playwright on desktop/tablet/mobile; `docker compose config -q` and `git diff --check` pass. The Docker runtime was not rebuilt.
- D3.js Knowledge Graph replacement: ESLint pass (1 warning on unused var, fixed), TypeScript pass, 12 Vitest tests pass, Next.js production build pass. Graph page reduced from 142 kB to 28.6 kB first load JS. D3 force-directed layout with charge -350, link distance 80, collision detection, zoom 0.15-4x, custom node shapes, hover/selected effects, and zoom controls all working.
- Knowledge Graph UI optimization: ESLint pass, TypeScript pass, 12 Vitest tests pass, Next.js production build pass. Reduced node size from 36px to 26px, increased font from 10px to 11px, added hover/selected effects, zoom controls (+/−/fit), collapsible filters/legend panels, improved layout parameters (gravity 0.35, repulsion 4500, edge length 70px), and better responsive behavior.
- Source-pipeline documentation: `git diff --check -- 'Docs/Source Processing Pipeline.md'` passes; the document has 14 balanced Markdown fences, all expected sections and one `flowchart TD` Mermaid block. Mermaid CLI is not installed in the repository, so the diagram received static syntax review rather than a rendered CLI validation.
- 2026-07-17 09:39 runtime start: `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d` completed successfully. `docker compose ps` reports all four core services up and PostgreSQL healthy; direct API health, frontend root, and proxied API health return HTTP 200 with `{"status":"ok"}` for both health paths. A fresh API/worker/frontend log scan found no `error`, `exception`, `traceback`, `fatal`, or HTTP 500 entries.
- DeepSeek/intake completion audit: official API `/models` returns HTTP 200 and includes configured `deepseek-v4-pro`; a live full-schema classification validates at confidence 0.95. GitHub, two articles, arXiv paper and direct PDF jobs completed with DeepSeek/model provenance in one attempt; Facebook Reel returned expected transcript-unavailable partial success; a private URL returned `INVALID_URL`; there are zero active jobs. One DeepSeek item was approved and is visible through PostgreSQL search and graph.
- Final gates: Ruff passes; 43 backend tests pass in Compose with only the existing upstream Starlette/httpx warning; frontend ESLint, TypeScript, 12 Vitest tests and Next.js production build pass; 12 Playwright tests pass on desktop/tablet/mobile; Compose config and Markdown fences pass. After the final image rebuild/recreate, direct/proxied health, all eight frontend routes, providers, search and graph return HTTP 200, invalid retry provider returns 422, PostgreSQL is healthy, and fresh API/worker/frontend logs contain no 500, traceback or exception.
- No-mock AI session: Ruff passes; 39 backend tests pass in an ephemeral Compose container with the existing Starlette/httpx deprecation warning; frontend ESLint, TypeScript, 12 Vitest tests and Next.js production build pass; Compose config validates. The rebuilt runtime reports only Ollama/OpenAI/DeepSeek/Gemini/OpenRouter/Mistral, marks configured Mistral active, rejects `provider=mock` with HTTP 422, returns HTTP 200 for health and `/ingestion`, and has clean API/worker/frontend startup logs.
- 2026-07-17 runtime start: `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d --build` completed successfully. All four core services are up, PostgreSQL is healthy, API health and proxied health return `{"status":"ok"}`, the frontend root returns HTTP 200, and the recent four-service log scan found no startup errors.
- Deep-ocean/provider session: backend Pytest `38 passed` with one existing Starlette/httpx deprecation warning; Ruff, frontend ESLint, TypeScript, 12 Vitest tests and Next.js production build all pass. Base and `local-ai` Compose configs plus `git diff --check` pass.
- Browser matrix: 12 Playwright tests pass on desktop, tablet and mobile using the Ollama option for live intake UI coverage; all eight primary routes return HTTP 200, health passes directly and through the frontend proxy, and no console/API/overflow errors were found.
- Accessibility checks: white on teal primary 5.92:1, white on indigo accent 4.73:1, topbar text 10.55:1, body text 7.82:1 and muted text 4.60:1; all checked pairs meet WCAG AA.
- Live source/provider matrix: GitHub + DeepSeek, Python.org article + local Ollama, and direct PDF + Mistral completed with structured classification; Facebook Reel + Mistral returned the expected metadata-only partial success. No source PDF/video artifacts were downloaded into `apps/`, and recent API/worker/frontend/bridge logs contain no error, exception or traceback.
- Runtime restart session: `docker compose config -q` passed; cached API/worker/frontend images rebuilt; all four Research System services started on 18000/13000 without touching `smart_exam_*`; API health and proxied health returned `{"status":"ok"}`, frontend root and API docs returned HTTP 200, and startup logs showed no errors.
- Smart Exam frontend session: ESLint, TypeScript, 12 Vitest tests and Next.js production build pass; npm audit reports 0 vulnerabilities.
- Browser matrix: 12 Playwright tests pass on desktop 1280+, tablet 1024x768 and mobile 390x844. All eight primary routes hydrate without console/API 500 errors, status badges contain no untranslated `status.*` keys, source submission works and no viewport overflows horizontally.
- Visual inspection covered dashboard, ingestion, research library/detail, graph, search, gaps, collector and training against the running Smart Exam reference. Computed tokens assert `#fafaf8`, `#e54b2b`, 999px action pills and absence of the old sidebar.
- Docker frontend image was rebuilt and recreated on `http://localhost:13000`; the rendered root contains the expected title, proxy health passes and container logs show a clean compile. Base Compose recreation was verified with `NEXT_PUBLIC_API_URL` unset.

- Stabilization session: backend Pytest `34 passed` (one upstream TestClient deprecation warning) and Ruff pass.
- Frontend: Vitest `12 passed`, Playwright `6 passed` across desktop/tablet, ESLint/typecheck pass, and Next.js 15 production build pass for all application routes.
- Live-source matrix on the Compose stack covered invalid/private URL rejection, generic article, text-layer PDF, public Facebook metadata, arXiv, conventional DOI, and GitHub repository/file/issue/pull request. The worker continued after failures and persisted typed outcomes.
- Clean-start: a separate Compose project with fresh PostgreSQL and frontend volumes reached migration `73f6a8c1d2e0`; API/proxy health passed and a real URL job completed. Test containers and volumes were removed afterward.
- `docker compose config -q` and `git diff --check` pass. The main database/api/worker/frontend stack remains available on 18000/13000.

- Docker rebuild session: API/worker/frontend images built successfully; Compose startup initially hit the known external port-8000 conflict, then succeeded with documented 18000/13000 overrides. Health, graph API and all eight primary frontend routes pass; recent service logs contain no runtime errors.
- Current session: Ruff pass; 23 backend tests pass with the existing TestClient deprecation warning.
- Frontend: 5 Vitest tests pass; ESLint, TypeScript and Next.js production build pass; npm audit reports 0 vulnerabilities during install.
- Runtime: Docker database/api/worker/frontend are running on 18000/13000; health and all primary routes return HTTP 200.
- Live graph smoke: 8 unique nodes, 4 edges, zero dangling edges, valid meta/provider, and bounded neighbor response.
- `docker compose config -q` passes. Workspace still is not recognized as a Git repository despite a `.git` directory.

- Intake resubmission fix: Ruff pass; 16 tests pass; ESLint/build pass. Live `wailsapp/wails` resubmission changed OpenRouter dead-letter to DeepSeek queued, then reached `needs-review` after one worker attempt with structured classification.
- Mistral session: Ruff pass; 15 tests pass; Compose config pass; live provider registry returns Mistral without exposing keys; API and worker restart cleanly on ports 18000/13000.
- Current worker session: Ruff pass; 14 tests pass; SQLite migration upgrade/downgrade/upgrade pass; ESLint and Next.js production build pass; Compose config pass.
- Runtime smoke: Docker services `database`, `api`, `worker`, and `frontend` are running; PostgreSQL migration `4a6e8b2c9d10` applied; health and every primary frontend route return HTTP 200 on ports 18000/13000; seed contains one research item.
- Backend: Ruff pass; 12 tests pass. Link-intake migration upgrade/downgrade/upgrade pass trên SQLite và upgrade pass trên PostgreSQL.
- Frontend: ESLint/typecheck pass; Next.js production build pass (10 app routes plus not-found); npm audit reports 0 vulnerabilities.
- Docker: `docker compose config -q` pass; current smoke health API and every primary route (`/ingestion`, `/graph`, `/research`, `/search`, `/collector`, `/gaps`, `/training`) return HTTP 200 at ports 18000/13000.
- Markdown code fences và `docker compose config -q` pass.
- Git status không có vì workspace không phải Git repository.
