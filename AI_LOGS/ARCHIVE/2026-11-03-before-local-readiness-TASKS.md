# Task Board

## Now

Tiếp tục kỹ thuật (2026-11-03, `US-CONTAINER-RUNTIME-HARDENING`): API/worker non-root, root/source
chỉ đọc, volume cũ tương thích và bản sửa giới hạn tiến trình LaTeX đã chạy trên runtime thật.
582 test API cùng canary/migration/HTTP/autostart đạt; xem session ngày 03/11. Bước kỹ thuật tiếp
theo: sandbox CLI và chuyển cầu nối ra ngoài cây mã. Các bước đăng nhập/nhà cung cấp dưới đây vẫn chờ.

Gói ChatGPT riêng (2026-10-27, `US-CHATGPT-PLAN-CONNECT`): mã, test và runtime cục bộ đã xong.

- [ ] Linh thử thật: mở `http://localhost:13000/account` **trên chính máy chủ** → "Tiếp tục với
  ChatGPT" → đồng ý → tạo một cuộc chat với "Gói ChatGPT của tôi". Báo lại nếu OpenAI từ chối.
- [ ] Linh điền form đối tác https://openai.com/form/sign-in-with-chatgpt-interest/ để có client ID
  cho bản web; khi có: đặt `CHATGPT_PLAN_CLIENT_ID`, `CHATGPT_PLAN_CLIENT_SECRET`,
  `CHATGPT_PLAN_REDIRECT_URI=<PUBLIC_URL>/account/ai/callback`.
- [ ] (Tùy chọn) chế độ bắt buộc gói riêng cho việc do người dùng khởi chạy (máy chủ không trả AI).
- [ ] Kiểm tra lại khóa `OPENAI_API_KEY` (preflight không phản hồi) và Ollama (không chạy).

Tối ưu toàn diện (2026-10-24, `US-OPTIMIZATION-PROGRAM`): mã đã xong; còn các bước sau.

- [ ] Linh tạo chủ sở hữu cục bộ (`make local-owner NAME=... EMAIL=...`), rồi agent đặt
  `AUTH_MODE=local` trong `.env` và restart API/worker (cổng đã chỉ nghe 127.0.0.1).
- [ ] Linh quyết định bật nghiên cứu sâu cho người dùng: `RESEARCH_AGENT_ENABLED=true` trong `.env`,
  restart API/worker (SearXNG đã chạy). Chế độ nhóm cần `RESEARCH_AGENT_PROVIDER` là API.
- [ ] Gõ `/reload-plugins` để dùng plugin `frontend-design`, `claude-security`; chạy
  `scripts/install-git-hooks.sh` trên mỗi máy của nhóm.
- [ ] Cài cầu nối CLI ngoài cây mã (phần còn lại S9; non-root/mã chỉ đọc đã hoàn tất 2026-11-03).
- [ ] Thu hẹp sandbox cầu nối CLI: lọc keyring cho agy, không cho shell Codex đọc `auth.json` (S7).
- [ ] Giảm token pipeline nghiên cứu (eval: +42% so với naive do kiểm tra suy luận); `/chat` mobile
  Lighthouse 81. (E2E trên stack cô lập đã chạy 2026-10-27: 84/84.)
- [ ] Push nhánh `feature/research-system-mvp` khi Linh đồng ý.

Triển khai cho nhóm (2026-10-14): mã, cấu hình và runbook đã sẵn sàng; còn các bước của chủ sở hữu.

- [ ] Linh giải phóng dung lượng đĩa (cần ~8 GB trống, hiện ~2,8 GB) trước `make team-up`.
- [ ] Linh tạo `.env.team` từ `.env.team.example`, chọn lối vào HTTPS (Cloudflare Tunnel/Caddy),
  chạy `make team-backup`, `make team-db-password`, `make team-up`, `make team-owner`, rồi thêm thành
  viên ở `/members`. Hướng dẫn: `Docs/Team Deployment Runbook.md`.
- [ ] Linh rà soát và quyết định commit thay đổi phiên 03/11; trước phiên nhánh đã đi trước
  `origin/feature/research-system-mvp` 46 commit theo ref cục bộ (chưa fetch/push).
- [ ] Lên lịch `scripts/team.sh backup` hằng đêm và sao chép bản lưu ra ngoài máy.

- [ ] Linh tạo khóa Gemini miễn phí ở Google AI Studio và điền `GEMINI_API_KEY` vào `.env`; sau đó
  agent đặt `SEARCH_EMBEDDING_PROVIDER=gemini`, `SEARCH_EMBEDDING_MODEL=gemini-embedding-2`, restart
  API/worker, gọi thật và lập chỉ mục lại RAG tài liệu (story `US-GEMINI-EMBEDDING-API`).
- [ ] Linh thử một link thật và một cuộc chat trên `/ingestion`, `/chat` với Codex (mặc định
  mới), theo dõi quota gói Codex; đổi `AI_PROVIDER`/`GRAPH_CHAT_DEFAULT_PROVIDER` trong `.env`
  sang `claude_code` hoặc `antigravity` nếu muốn, rồi `systemctl --user restart
  business-ai-agents.service`. Quay lại API: khôi phục `.env.before-cli-bridge-*`.
- [ ] Tắt quick tunnel khi không còn dùng điện thoại:
  `systemctl --user stop business-ai-agents-quick-tunnel` và
  `docker rm -f businessaiagents-tunnel-gate` (đang mở từ 2026-10-23, có basic auth).

Trạng thái runtime ngày 2026-10-23: bốn container của project đang chạy (autostart);
quick tunnel Cloudflare + cổng mật khẩu nginx đang bật để truy cập từ điện thoại.

`Docs/Business AI Agents Completion Goal.md` (Harness intake #19) is fully implemented, and
a follow-up defect sweep (intake #20) fixed seven further issues across frontend, backend
and database. All five stories passed `harness-cli story complete` with their real proof
commands. What remains are owner decisions, not engineering work.

- [ ] Linh reviews live change set `5759af2f-4685-4cfa-b360-39d7981a1fa4`, completes the
  Graph v2 product-owner walkthrough, and records the rollout decision.
- [ ] Linh reviews link change set `42ae7795-280e-4ee1-8525-2462cc061074`, produced by the
  new intake-to-hierarchy path from `https://arxiv.org/abs/2210.03629` (16 mutations, 16
  valid, 0 errors), and decides whether to apply it.

## Later

- [ ] Chuẩn hóa khóa tag/ontology giữ dấu tiếng Việt (hiện `máy`→`m-y`, nhãn chỉ khác dấu bị gộp);
  cần migration tính lại khóa + gap keys.
- [ ] Tiêu thụ hoặc bỏ `outbox_events` (đang chỉ ghi); cân nhắc tự cập nhật bản chiếu pgvector khi duyệt.
- [ ] Rate limit/metrics dùng chung (Redis hoặc PostgreSQL) nếu chạy nhiều máy/nhiều worker.
- [ ] Quyết định phạm vi chuyển sang OpenRouter free (2026-10-12 đã đánh giá): chỉ đổi
  `AI_PROVIDER` (không code) hay thêm graph chat/embedding OpenRouter (cần code, embedding
  cần khớp 1024 chiều hoặc migration + re-index). Session:
  `AI_LOGS/SESSIONS/2026-10-12-0945-openrouter-free-assessment.md`.
- [ ] Decide whether a future layout-faithful DOCX/PDF authoring/export engine is needed. Current
  post-upload editing safely versions AI-readable UTF-8 derivatives and preserves the original
  binary, but deliberately does not round-trip Office/PDF layout.
- [ ] Decide whether to batch-rebuild RAG for the three legacy workspaces backfilled by migration
  `2d4e6f8a0b13`; they are visible as `pending` and can be rebuilt individually without re-upload.
- [ ] Extend background processing to scheduled collectors and add optional Redis transport.
- [ ] Add more collector adapters after RSS is validated.
- [ ] Add deployment-owned telemetry retention/alerts, backup and remaining production hardening.
- [ ] Run the Discord gateway against a real Discord application. The code, image and
  Compose profile are complete; only a bot token and an allowlisted server are missing, and
  both are the owner's to provide.
- [ ] Persist HTTP validators between submissions so conditional GET saves a download across
  jobs, not only within one fetch. Needs a schema column.

## Blocked

- [ ] Complete product-owner Graph v2 acceptance.
  - Engineering proof is complete: DeepSeek preflight is ready and a real scoped brainstorm created
    a valid draft-only proposal. Only Linh can inspect the result, complete the walkthrough and
    record the rollout decision. OpenAI credential replacement is optional follow-up.
- [ ] Obtain product-owner acceptance on the redesigned Vietnamese research workspace across the
  dashboard, intake, research and graph surfaces.
  - Blocker: only Linh can record product usability/rollout acceptance.
- [ ] Default API host port 8000 is unavailable in the current environment.
  - Blocker: unrelated `smart_exam_backend` container owns port 8000.
  - Workaround: use `API_PORT=18000 FRONTEND_PORT=13000` as documented.

## Done

- [x] Gia cố container API/worker (2026-11-03, intake #15 / `US-CONTAINER-RUNTIME-HARDENING`
  / DEC-066): UID/GID 10001, mã/root chỉ đọc, zero capabilities/no-new-privileges, tmpfs/PID
  bounds, init quyền volume không theo symlink; sửa LaTeX để không vướng nproc theo UID dùng chung.
  API 582, Ruff, ba Compose config, canary ảnh và hai container thật, OCR/PDF/restore,
  PostgreSQL tạm upgrade/check, HTTP tiếng Việt và autostart đạt; toàn bộ hash DB/tệp khớp.
  Backup ngoài repo; runtime 13000/18000 khỏe; chưa commit/push. Session:
  `AI_LOGS/SESSIONS/2026-11-03-1138-container-runtime-hardening.md`.

- [x] Rà soát luồng + sẵn sàng triển khai nhóm (2026-10-14, intake #10 / `US-TEAM-DEPLOYMENT-READINESS`
  / DEC-061): chế độ `docker-compose.team.yml`, `scripts/team.sh`, `/members`, `/account`, runbook;
  sửa lỗi phân quyền xuất bản, XSS tệp gốc, SSRF RSS, duyệt nguyên tử, worker/lease, rate limit,
  hết phiên/phân trang frontend. API 401, Discord 55, frontend 180, build runner, E2E stack nhóm cô
  lập đạt; runtime cục bộ đã cập nhật sau sao lưu. Session:
  `AI_LOGS/SESSIONS/2026-10-14-2330-team-deployment-readiness.md`.
- [x] Tạm dừng bốn container của project để so sánh RAM (2026-10-12 22:19 UTC+7):
  RAM dùng 8,021 → 7,244 GiB ở lần đo cuối, giảm 795,57 MiB; giữ nguyên volume,
  container và các project khác. User service đã stop, autostart vẫn enabled. Session:
  `AI_LOGS/SESSIONS/2026-10-12-2217-stop-project-ram-check.md`.
- [x] Kiểm tra read-only RAG (2026-10-12): có trong code cho chat phạm vi tài liệu,
  nhưng runtime chưa hoạt động (2 workspace `pending`, 0 chunk; vector provider
  `postgres`). Session: `AI_LOGS/SESSIONS/2026-10-12-0930-rag-check.md`.
- [x] Khảo sát read-only luồng hoạt động chính (2026-10-12): intake URL, tài liệu,
  change set đồ thị, chat; đối chiếu số liệu DB thật. Session:
  `AI_LOGS/SESSIONS/2026-10-12-0915-main-flow-survey.md`.
- [x] Kiểm tra read-only frontend Docker cổng 13000 (2026-10-12): xác nhận container
  `businessaiagents-frontend-1` publish `13000->3000`, healthy, production standalone từ
  source bind-mount; HTTP 200. Session:
  `AI_LOGS/SESSIONS/2026-10-12-0900-frontend-docker-port-check.md`.
- [x] Chọn model và kiểm tra API cá nhân trước khi kết nối (intake #9 /
  `US-CHAT-API-VALIDATION` / DEC-060): model list động, probe có giới hạn theo nút bấm,
  lỗi key/credit/quota/quyền/model/tốc độ/mạng, stale-result guard và model phiên cũ.
  Không migration/lưu key/call thật. 380 API + 171 frontend + lint/type/build đạt;
  15 E2E production responsive đạt, API/frontend đã cập nhật, giữ 10 sessions/32 messages.
  Session: `AI_LOGS/SESSIONS/2026-09-05-1521-chat-api-model-validation.md`.

- [x] Cho phép API cá nhân OpenAI/DeepSeek trong chat (intake #8 / high-risk
  `US-PERSONAL-CHAT-API` / DEC-059): nhập password/model, bộ nhớ theo trang/tài khoản,
  xóa khóa, create/import/send nguồn personal, không fallback hệ thống khi thiếu key.
  Migration `3e5f7a9b1c24`; giữ 10 sessions/32 messages. Ruff, 334 API tests, 14 frontend
  unit, TypeScript/ESLint, 15-route build và 12 responsive E2E đạt; runtime `13000/18000`
  đã cập nhật. Session: `AI_LOGS/SESSIONS/2026-09-05-1446-personal-chat-api.md`.

- [x] Thiết kế lại nội dung và UI trò chuyện AI theo ảnh ngày 2026-09-05 (intake #7 /
  `US-AI-CHAT-REDESIGN`): lịch sử tìm kiếm không dấu, gợi ý nghiên cứu, biểu mẫu tạo/nhập
  trong cột chính, ô nhập trong viewport, Enter/Shift+Enter/IME, mobile thu gọn lịch sử,
  lỗi lịch sử tiếng Việt kèm mã chi tiết. ESLint, TypeScript, 11/11 unit, build production
  15 route và Playwright 9/9 đạt. Đã chạy trên `13000/chat` bằng restart riêng frontend;
  dữ liệu và các container còn lại giữ nguyên. Session:
  `AI_LOGS/SESSIONS/2026-09-05-1414-ai-chat-redesign.md`.

- [x] Thiết kế lại giao diện theo mô hình không gian làm việc nghiên cứu (Harness intake #6 /
  normal story `US-RESEARCH-WORKSPACE-UI-REDESIGN` / DEC-058): desktop có sidebar chia nhóm và
  thanh ngữ cảnh; tablet/mobile giữ toàn bộ tuyến bằng điều hướng ngang; dashboard, token, form,
  button, card, table và tiêu đề trang có phân cấp mới, phẳng và dễ đọc hơn. Không đổi API, URL,
  quyền hoặc nghiệp vụ. ESLint, TypeScript, 146/146 Vitest, build 15 route, Playwright desktop /
  tablet / mobile, ảnh kiểm tra trực quan và 6/6 smoke test trên container production đều đạt. Chỉ
  frontend Docker được build/recreate; API, worker, database/volume và Smart Exam không đổi.
  Harness completion, decision verification, standard trace #6 và audit entropy `0/100` đạt.
  Session: `AI_LOGS/SESSIONS/2026-09-04-1655-research-workspace-ui-redesign.md`.

- [x] Build lại runtime Docker tiếng Việt (Harness intake #5 / normal story
  `US-REBUILD-VIETNAMESE-DOCKER-RUNTIME`): build tuần tự image API/worker/frontend và recreate ba
  container ứng dụng bằng cấu hình multi-user trên `18000`/`13000`; giữ nguyên database container,
  PostgreSQL volume và ID hai container Smart Exam. Direct/proxied health, frontend, 11 route,
  HTML `lang="vi"`, readiness, migration head, graph 45/32, autostart và log mới đều đạt. Chỉ cache
  build không còn dùng bị xóa; dung lượng trống tăng từ 1,6 GB lên 11 GB. Harness completion và
  detailed trace #5 đạt. Session:
  `AI_LOGS/SESSIONS/2026-09-04-1221-rebuild-vietnamese-docker-runtime.md`.

- [x] Chuyển các bề mặt sản phẩm sang tiếng Việt tự nhiên, nhất quán cho người làm nghiên cứu
  (Harness intake #4 / story `US-FULL-VIETNAMESE-EXPERIENCE` / DEC-057). Gỡ bộ chuyển EN/VI,
  cố định HTML ở `vi`, Việt hoá giao diện web, nội dung trợ năng, thông báo an toàn của API và cổng
  Discord, cùng README/tài liệu cốt lõi. Giữ nguyên mã lỗi, API, khóa JSON, tên công nghệ và dữ liệu
  nghiên cứu gốc. ESLint, TypeScript, 145 frontend tests, bản dựng 15 route, Ruff + 323 backend
  tests, Ruff + 55 Discord tests, 45 E2E desktop/tablet/mobile, kiểm tra chuỗi hiển thị, Markdown và
  `git diff --check` đều đạt; Harness completion và detailed trace #4 đã được ghi. Session:
  `AI_LOGS/SESSIONS/2026-09-04-1156-full-vietnamese-experience.md`.

- [x] Sweep the complete Desktop project for reproducible defects (Harness intakes #2/#3; normal
  story `US-FULL-PROJECT-DEFECT-SWEEP-2026-08-24` plus high-risk security story
  `US-FRONTEND-DEPENDENCY-SECURITY-2026-08-24`). Fixed dev-tool isolation, deterministic frontend
  dependency installs/synchronization, container-safe TypeScript checks, current Next.js 15.5
  dependency findings and tablet modal E2E targeting. API 323, Discord 55, frontend 145 and
  Playwright 69 enabled tests pass; audit is zero, builds/migrations/graph/runtime/routes/autostart
  pass, persistent Business AI Agents data remains intact, and no command targeted Smart Exam; its
  service remains healthy on `8080`. Full API image rebuild remains an
  optional disk-capacity task because the uncached TeX/OCR layer was safely interrupted at 96% root
  usage; code and the live API image are verified. Both Harness stories complete; traces #2/#3 meet
  their lane tiers and audit entropy is 0/100. Session:
  `AI_LOGS/SESSIONS/2026-08-24-2352-full-project-defect-sweep.md`.

- [x] Repair Desktop autostart after the repository move (Desktop Harness intake #1 / normal story
  `US-LOCAL-RUNTIME-AUTOSTART`). Recovered 193 missing application files plus 842 repository/support
  files from the interrupted move without overwriting files already on Desktop; removed the launcher's stale NTFS mount
  dependency; pinned Compose identity; installed/enabled the user service; and recreated only the
  three source-bound application containers. Database/named volumes were preserved. Service state,
  restart policies, Desktop bind sources, direct/proxied health, readiness, migration head, graph
  invariants, three frontend routes and an idempotent restart pass. Smart Exam `8080` retained all
  container IDs. Desktop Harness completion passes; detailed trace #1 meets 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-24-2319-desktop-autostart-repair.md`.

- [x] Restore the local project after the NTFS volume mounted as `Data1` while the autostart launcher
  still targeted the stale `Data` path. Stopped the failing user-service loop, preserved PostgreSQL
  and named volumes, and recreated API/worker/frontend from the real repository. All four services
  are running on `18000`/`13000`; health/readiness, migration head, graph invariants, three frontend
  routes, fresh logs and bind sources pass. The fixed-path autostart follow-up was completed on
  2026-08-24.
  Session: `AI_LOGS/SESSIONS/2026-08-16-1514-restore-local-project.md`.

- [x] Keep `/graph/system` text above every hierarchy card (intake #79 / normal story
  `US-SYSTEM-MAP-FOREGROUND-LABELS`, intervention #28): System root, pillar, action/count and
  expanded child text now renders in the existing foreground SVG label group with a 2.5px outline
  and no pointer events, while the interactive source cards retain accessible names. Live Chrome
  proves 12/12 overlays collapsed and 45/45 expanded with zero overflow/errors and unchanged
  folding/containment. ESLint, 144/144 tests, TypeScript, build, responsive E2E 3/3 and Harness
  completion pass. Standard trace #81. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1524-system-map-foreground-labels.md`.

- [x] Keep Network community headings above node glyphs (intake #78 / normal story
  `US-KNOWLEDGE-GRAPH-COMMUNITY-LABEL-LAYER`, intervention #27): halo circles remain behind the
  graph, but the type/count headings now use the existing foreground label group with a 3px
  canvas-colored outline and no pointer events. Live 429-node proof found five real intersections
  and confirms all headings paint above nodes with zero overflow/errors. ESLint, 144/144 tests,
  TypeScript, build, responsive E2E 3/3 and Harness completion pass. Standard trace #80. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1134-knowledge-graph-community-label-layer.md`.

- [x] Remove redundant visible prose from primary Knowledge Graph (intake #77, tiny): kept the
  title, functional labels, nodes, compact counts and important runtime states while removing the
  repeated page intro, hierarchy explanation banners, canvas guide and interaction helper. The
  bottom status now compactly reports semantic links, hidden leaves and unplaced nodes. Live
  1920×1080 proof has zero guide/banner elements, `97.0%` studio width, zero overflow/errors;
  ESLint, 144/144 tests, TypeScript, build and responsive E2E 3/3 pass. Standard trace #79. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1122-knowledge-graph-text-cleanup.md`.

- [x] Expand the primary Knowledge Graph to the wide viewport (intake #76 / normal story
  `US-KNOWLEDGE-GRAPH-FULL-VIEWPORT`, intervention #26): `/graph` alone bypasses the shared 1440px
  reading cap and uses responsive gutters plus a taller wide-screen canvas. At the owner's
  1920×1080 size, the live studio grew from approximately 1224px/63.8% to 1862.4px/97.0%, with an
  1860.4×864px canvas, 107% readable zoom, zero horizontal overflow and zero browser errors. Other
  routes retain their width. ESLint, 144/144 tests, TypeScript, build and responsive Playwright 3/3
  pass. Harness completion and standard trace #78 are recorded. Session:
  `AI_LOGS/SESSIONS/2026-08-14-1048-knowledge-graph-full-viewport.md`.

- [x] Scale concurrent Knowledge Graph reads (intake #75 / normal story
  `US-KNOWLEDGE-GRAPH-CONCURRENT-LOAD`): initial Hierarchy now uses two graph reads instead of a
  third full `/graph/stats` projection; browser graph/neighbor reads are deduplicated for a bounded
  interval; gzip cuts the real response from 297,275 to 28,443 bytes; and the autostart runtime uses
  four Uvicorn workers, controlled PostgreSQL pools and standalone production Next.js. A 60-request,
  concurrency-20 proxy benchmark passes 60/60 at 130.13 ms average versus 457.53 ms baseline. API
  323/323, frontend 143/143, lint/typecheck/build, responsive E2E 3/3, Compose, readiness and
  idempotent health-aware autostart pass. Harness completion and standard trace #77 are recorded.
  Shared exposure still requires auth/TLS and a shared gateway/rate limiter. Session:
  `AI_LOGS/SESSIONS/2026-08-14-0956-knowledge-graph-concurrent-load.md`.

- [x] Fit and smooth the Knowledge Graph workspace (intake #74 / normal story
  `US-KNOWLEDGE-GRAPH-FIT-SMOOTH`): explicit Fit now contains every card in the expanded real
  91-node hierarchy at desktop/tablet/mobile instead of leaving 63–64 outside; the zoom badge tracks
  the actual transform; resize is frame-coalesced; and hierarchy hover updates only its card and
  indexed incident edges with zero transitions. Full ESLint, 31 Vitest files / 141 tests and
  responsive Playwright 3/3 pass; Harness completion and standard trace #76 are recorded. The
  follow-up concurrent-runtime story repaired the document-editor fixture and restored full
  TypeScript/build proof. Session:
  `AI_LOGS/SESSIONS/2026-08-14-0937-knowledge-graph-fit-smoothness.md`.

- [x] Auto-start the core local runtime (intake #73 / normal story
  `US-LOCAL-RUNTIME-AUTOSTART`): database, API, worker and frontend now use
  `restart: unless-stopped`; a mount-aware enabled systemd user service restores the stack after
  desktop login on API `18000` / frontend `13000` without rebuilding images. Compose validation,
  installed-service validation, direct/proxied health, frontend HTTP 200, readiness and idempotent
  restart proof pass. Smart Exam on `8080` remained running with unchanged container IDs. Session:
  `AI_LOGS/SESSIONS/2026-08-14-0917-local-runtime-autostart.md`.

- [x] Simplify Uploaded documents and add safe edit/delete controls (intake #72 / high-risk story
  `US-DOCUMENT-LIBRARY-SIMPLIFY-DELETE` / DEC-055): the responsive list now contains Document,
  bounded Summary, Size and Actions; Edit opens the existing workspace; only owners see confirmed
  Delete. The API blocks active jobs, intake-retained documents and applied graph provenance, and a
  permitted delete cleans workspace/research derivatives, draft proposals, chat, projections and
  object versions while retaining a content-free audit record. Ruff, focused API 38/38, focused
  frontend 10/10, ESLint, build and responsive Playwright 3/3 pass. Detailed trace #74. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1710-document-library-summary-safe-delete.md`.

- [x] Remove the Document Workspace manual draft deletion path while preserving crash-safe local
  autosave (intake #71 / high-risk story `US-DOCUMENT-DRAFT-AUTOSAVE-ONLY` / DEC-054): every
  title/format/content edit still writes synchronously to the bounded identity-scoped browser cache;
  refresh and route reopen restore exact content; failed Create retains it; successful governed
  Create is now the only product event that clears it. The discard handler/button and EN/VI copy are
  gone. Focused 24/24, full frontend 138/138, lint/typecheck/build, responsive Playwright 3/3 and
  rebuilt runtime health/readiness/log proof pass. Detailed trace #72 meets tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1548-document-draft-autosave-only.md`.

- [x] Keep the current local project running for owner review without rebuilding images or changing
  code/data. Database, API, worker and frontend are up on `18000`/`13000`; health/readiness,
  migration head, graph invariants, `/`, `/graph`, `/graph/system` and recent-log scan pass. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1521-run-local-project.md`.

- [x] Make the Business AI Agents system map progressive and type-explicit (intake #70 / normal
  story `US-SYSTEM-MAP-PROGRESSIVE-TYPES`): initial view is root + eleven collapsed pillars with
  actual `SYSTEM ROOT` / `SYSTEM PILLAR` headers, never generic `BOARD`. Opening the populated
  pillar contains all 33 direct children inside its compound board and closing restores 12 cards;
  the inspector says `System Pillar`. Canonical graph data is unchanged. Live `12 → 45 → 12`,
  33/33 containment and zero-error proof pass alongside lint/typecheck, 138/138 tests, build and
  responsive Playwright 3/3. Intervention #25 / standard trace #71. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1418-system-map-progressive-types.md`.

- [x] Show explicit node type in the hover-only Network badge (intake #69 / normal story
  `US-KNOWLEDGE-GRAPH-HOVER-TYPE`): resting type/name counts remain zero, while hover/focus reveals
  exactly one two-line type + name badge using the existing human-readable formatter and semantic
  color. Real 429-node / 370-edge Chrome proof shows `COLLECTOR SOURCE` above `OpenAI News`, 68
  direct edges, zero browser errors and unchanged faint dashed overview edges. Lint/typecheck,
  136/136 tests, build and responsive Playwright 3/3 pass. Intervention #24 / standard trace #70.
  Session:
  `AI_LOGS/SESSIONS/2026-08-11-1345-network-hover-type.md`.

- [x] Make Network node names uniformly hover-only (intake #68 / normal story
  `US-KNOWLEDGE-GRAPH-HOVER-LABELS`): zero labels render at rest independent of rank/degree/zoom,
  exactly one appears on local mouse/keyboard focus, leave restores zero, and click selection does
  not expose a label batch. Faint dashed overview edges and indexed direct-edge reveal remain intact.
  Live 429-node proof reports label counts `0 → 1 → 0`, zero selected-away labels, exact 68-edge
  reveal and no browser errors. Lint/typecheck, 136/136 tests, build, focused Harness 34/34,
  responsive Playwright 3/3 and rebuilt runtime readiness pass. Intervention #23 / trace #69.
  Session: `AI_LOGS/SESSIONS/2026-08-11-1153-network-hover-labels.md`.

- [x] Add progressive Network connection reveal (intake #67 / normal story
  `US-KNOWLEDGE-GRAPH-EDGE-REVEAL`): resting edges are faint dashed orientation lines, hover reveals
  only the indexed incident edges as clear solid lines, leave restores the overview, and click focus
  remains intact. Real 429-node / 370-edge proof revealed exactly 68 edges for the highest-degree
  node and measured 0.118 ms average / 0.8 ms maximum across 50 hover cycles with no long tasks,
  transitions, errors or residual classes. Lint/typecheck, 136/136 tests, build, focused Harness
  34/34, responsive Playwright 3/3 and rebuilt runtime readiness pass. Trace #68. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1142-network-edge-reveal.md`.

- [x] Remove the remaining whole-SVG paint lag on Network hover (intake #66 / normal story
  `US-KNOWLEDGE-GRAPH-HOVER-PAINT-PERF`): hover is local-only, click retains indexed neighborhood
  focus, the force layout is pre-settled and stopped, and delayed fits/inherited cursor writes/SVG
  filters were removed. Real 429-node / 370-edge Chrome proof reports 0.068 ms average and 0.4 ms
  maximum forced-style hover, 16.357 ms average frames, no post-switch long tasks, transitions or
  browser errors, and stable node positions. Lint/typecheck, 136/136 tests, build, focused Harness
  34/34, responsive Playwright 3/3 and rebuilt runtime readiness pass. Intervention #22 / trace #67.
  Session: `AI_LOGS/SESSIONS/2026-08-11-1133-network-hover-paint.md`.

- [x] Remove full-Network hover lag and compact graph icons further (intake #65 / normal story
  `US-KNOWLEDGE-GRAPH-NETWORK-HOVER-PERF`): focus is now an indexed incremental CSS-class update,
  not hundreds of D3 transitions/full DOM scans. Real 429-node benchmark averages 0.035 ms per
  enter/leave cycle with zero transition owners/errors. Toolbar/zoom/guide icons are 9/10/12 px,
  painted nodes are smaller and hit targets remain 44 px. Lint/typecheck, 136/136 tests, build,
  focused Harness 34/34, responsive Playwright 3/3 and rebuilt runtime health pass. Trace #66 meets
  standard tier. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1107-network-hover-performance.md`.

- [x] Switch the research graph to a light canvas with compact icons (intake #64 / normal story
  `US-KNOWLEDGE-GRAPH-LIGHT-CANVAS`): white/light graph chrome, 11 px toolbar icons, 12 px zoom
  icons and smaller Network/Orbit glyphs now match the application while invisible 44 px hit
  targets preserve easy selection. Computed browser styles, live screenshot, lint/typecheck,
  135/135 tests, build, focused Harness 33/33, responsive Playwright 3/3 and rebuilt runtime health
  pass. Trace #65 meets standard tier. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1047-light-graph-canvas.md`.

- [x] Build a GitNexus-inspired progressive graph studio (intake #63 / normal story
  `US-KNOWLEDGE-GRAPH-GITNEXUS-EXPLORER`): add Network/Hierarchy/Orbit layouts, type communities,
  semantic zoom, a dark canvas/status/inspector shell, bounded leaf previews with local expansion,
  and accepted semantic cross-links inside hierarchy boards. Real-data and responsive proof pass;
  frontend lint/typecheck, 134/134 tests, production build, Harness verification 32/32 and
  Playwright desktop/tablet/mobile 3/3 are green. Trace #64 meets standard tier; runtime remains
  live on `18000`/`13000`. Session:
  `AI_LOGS/SESSIONS/2026-08-11-1028-gitnexus-graph-studio.md`.

- [x] Restart the existing local project for owner review without rebuilding images or changing
  application code/data. Database, API, worker and frontend are running on `18000`/`13000`;
  direct/proxied health, `/`, `/graph`, readiness, migration head, graph invariants and fresh-log
  scan pass. Session: `AI_LOGS/SESSIONS/2026-08-11-0943-start-local-project.md`.

- [x] Redesign the research knowledge graph for readable exploration (intake #62 / normal story
  `US-KNOWLEDGE-GRAPH-VISUAL-REDESIGN`): hierarchy is now a multi-column atlas of 91 connected nodes
  with 338 unplaced nodes reported honestly; relationship keeps all 429 nodes with semantic zoom,
  hub-priority labels and neighborhood emphasis. Canvas-first responsive layout, optional explorer
  rail and contextual inspector replace the permanent side columns. Frontend 130/130,
  lint/typecheck/build, focused verification 28/28, Playwright 6/6 and live responsive/runtime
  proof pass. Session:
  `AI_LOGS/SESSIONS/2026-08-10-2350-knowledge-graph-visual-redesign.md`.

- [x] Restart the existing local project on the documented conflict-free ports without rebuilding
  images or changing application code/data. Database, API, worker and frontend are running on
  `18000`/`13000`; direct/proxied health, frontend, readiness, migration head, graph invariants and
  fresh-log scan pass. Session:
  `AI_LOGS/SESSIONS/2026-08-10-2309-start-local-project.md`.

- [x] Complete document-scoped graph analysis and synchronized global graph views (intake #61 /
  high-risk story `US-DOCUMENT-KNOWLEDGE-GRAPH-WORKSPACE` / DEC-053): all readable uploads get an
  isolated graph; `View analysis`, bounded source summaries, independent AI comparison and governed
  research-to-draft-change-set flow are live. Relationship/hierarchy share the same approved research
  corpus up to 1,000 nodes/4,000 edges; the Business AI Agents map is separate at `/graph/system`.
  Backend 316/316, frontend 123/123, lint/type/build, focused Playwright 2/2 and rebuilt Compose
  runtime/parity proof pass; detailed Harness trace #62 meets tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-09-2254-document-knowledge-graph-workspace.md`.

- [x] Restart the existing local project on the documented conflict-free ports without rebuilding
  images or changing application code/data. Database, API, worker and frontend are running on
  `18000`/`13000`; direct/proxied health, frontend, readiness, migration head, graph invariants and
  fresh-log scan pass. Session:
  `AI_LOGS/SESSIONS/2026-08-09-2210-start-local-project.md`.

- [x] Audit and fix all reproducible frontend-owned errors (intake #60 / high-risk story
  `US-FRONTEND-FULL-DEFECT-SWEEP`): moved default Playwright artifacts away from a stale root-owned
  workspace directory and constrained the selected Graph inspector that caused 1287 px content at
  a 1280 px viewport. ESLint, TypeScript, frontend 122/122, 14-route build, full Playwright 66 pass
  / 6 expected auth skips, and independent real-data route audit 39/39 pass. Runtime remains healthy
  on `18000`/`13000`; detailed Harness trace #61 meets the required tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1602-frontend-full-defect-sweep.md`.

- [x] Make uploaded documents open their editable workspace from the list (intake #59 / normal
  story `US-DOCUMENT-LIST-OPEN-EDITOR`): filename and localized primary action now link to the
  existing detail/editor route. Full frontend 121/121, focused navigation/editor
  11/11, lint/typecheck, Document Playwright 24/24 and live 40,222-character DOCX click/editor proof
  pass. Session: `AI_LOGS/SESSIONS/2026-08-09-1532-open-uploaded-document-editor.md`.

- [x] Fix LaTeX/PDF preview display (intake #58 / normal story
  `US-LATEX-PREVIEW-DISPLAY-FIX`): use whole-page PDF fitting, clear stale compiled LaTeX output
  while a changed source recompiles, cancel obsolete work and revoke object URLs. Focused frontend
  32/32, ESLint, TypeScript and LaTeX Playwright 9/9 pass on desktop/tablet/mobile. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1512-fix-latex-pdf-preview.md`.

- [x] View and edit all successfully extracted uploads (intake #57 / high-risk story
  `US-DOCUMENT-UPLOADED-EDITING` / DEC-052): source formats retain direct editing; PDF/DOCX retain
  immutable originals and expose labelled editable text derivatives with version/save/AI/restore,
  worker reprocessing and RAG compatibility. Backend 313/313, frontend 118/118, lint/type/build and
  Playwright 21/21 pass; real DOCX runtime proof passes on `18000`/`13000`. Session:
  `AI_LOGS/SESSIONS/2026-08-09-1458-edit-uploaded-documents.md`.

- [x] Restart the existing local project on the documented conflict-free ports without rebuilding
  images or changing application code/data. Database, API, worker and frontend are running on
  `18000`/`13000`; health, proxy, frontend, readiness, migration head and graph invariants pass.
  Session: `AI_LOGS/SESSIONS/2026-08-09-1427-start-local-project.md`.

- [x] Fix selection options disappearing after closing the edit window with a pending review
  (follow-up to intake #56 / `US-DOCUMENT-FOCUS-EDIT-WINDOW`): `closeFocusWindow` in
  `DocumentAuthoring` and `DocumentAIEditor` now discards the pending reviewed edit, so re-selecting
  text shows the action popover again. Regression tests in both suites; frontend 117/117, ESLint,
  TypeScript pass; rebuilt live. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1645-fix-selection-options-after-window-close.md`.

- [x] Two-pane focus edit window with persistent chat history (intake #56 / normal story
  `US-DOCUMENT-FOCUS-EDIT-WINDOW` / DEC-051): initial view shows document content only; selection
  options open a full-screen window (left text, right chatbot) with ✕/Escape close; edits persist on
  exit; chatbot pane has a per-document History toggle (localStorage). Frontend 115/115, ESLint,
  TypeScript pass; rebuilt live on `13000`. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1640-focus-edit-window-chat-history.md`.

- [x] Route document selection actions into the brainstorm chat panel (intake #55 / normal story
  `US-DOCUMENT-SELECTION-CHAT-ROUTING` / DEC-050): popover options post a user message in the chat
  and the reviewed AI edit card renders inside the chat thread; Ask AI + pane-title edit focus the
  composer; below-editor feedback and `document-custom-ai` input removed. Focused 20/20 + new routing
  test, ESLint, TypeScript pass; frontend rebuilt live on `13000`. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1330-selection-actions-into-chat-panel.md`.

- [x] Polish Document workspace editor + brainstorm UI (intake #54 / normal story
  `US-DOCUMENT-UI-POLISH`): elevated surfaces, chat bubbles/avatars, sticky brainstorm, smoother
  review cards and motion. Focused frontend 27/27, ESLint, TypeScript pass. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1048-document-ui-polish.md`.

- [x] Hunt and fix hidden Document Brainstorm bugs (intake #53 / high-risk story
  `US-DOCUMENT-BRAINSTORM-HIDDEN-BUGS` / DEC-049): stale selection normalize, instant-edit success
  boolean, chat ready/failed/busy feedback, lock send/apply during busy/pending review, and block
  advisory Apply that breaks standalone LaTeX. Frontend focused 27/27, ESLint, TypeScript and backend
  document brainstorm/instant-edit 20/20 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-07-1035-document-brainstorm-hidden-bugs.md`.

- [x] Preserve sensitive values across cloud document edits and diagnose LaTeX errors (intake #52 /
  intervention #20 / high-risk story `US-DOCUMENT-REDACTION-ROUNDTRIP` / DEC-048): unique ephemeral
  tokens replace generic output-capable placeholders, exact originals restore locally before review
  and every leaked/missing/altered marker fails closed. XeLaTeX now returns bounded line/reason
  diagnostics. Backend 312/312, Ruff, live compile and real DeepSeek privacy/round-trip proof pass.
  ESLint, TypeScript and responsive Playwright 18/18 also pass.
  Session: `AI_LOGS/SESSIONS/2026-08-04-2320-redaction-roundtrip-latex-errors.md`.

- [x] Keep long successful Document AI edits connected through the frontend proxy (intake #51 /
  intervention #19 / high-risk story `US-DOCUMENT-PROXY-LONG-SUCCESS` / DEC-047): replace the
  disproven 125-second budget with a bounded, deploy-visible 180-second default after live evidence
  showed API HTTP 200 at 131.115 seconds following a frontend socket reset. Rebuilt runtime is back
  on `13000` with effective `API_PROXY_TIMEOUT_MS=180000`; frontend 110/110, lint/typecheck/build,
  Playwright 15/15 and a real post-restart DeepSeek HTTP 200 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-2301-document-proxy-180s.md`.

- [x] Preserve whole-source LaTeX integrity for AI edits (intake #50 / intervention #18 /
  high-risk story
  `US-DOCUMENT-LATEX-EDIT-INTEGRITY` / DEC-046): explanatory prose, Markdown fences, missing source
  boundaries and trailing commentary now fail closed at API and browser boundaries before Accept;
  Raw remains unchanged. Valid complete rename patches remain reviewed. Real DeepSeek proxy proof,
  backend 307/307, frontend 109/109, lint/typecheck/build and Playwright 15/15 pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-2230-latex-edit-source-integrity.md`.

- [x] Route direct contextual-chat edit commands to reviewed document patches (intake #49 /
  intervention #17 / high-risk story `US-DOCUMENT-CHAT-EDIT-INTENT` / DEC-045): `sửa`, `thay`, `đổi`, `replace`,
  `rename` and other bounded imperatives reuse the conflict-safe custom instant-edit path, render
  complete Original/Proposed content and require Accept or Reject. Advisory questions still use
  Brainstorm. Live Chrome, real DeepSeek, backend 11/11, Ruff, frontend 106/106,
  lint/typecheck/build and Playwright 12/12 pass. Detailed trace #54 meets high-risk tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1659-document-chat-reviewed-edits.md`.

- [x] Recover safely from Document Brainstorm timeouts (intake #48 / intervention #16 / high-risk story
  `US-DOCUMENT-BRAINSTORM-RELIABILITY` / DEC-044): raw DeepSeek errors are replaced with localized
  feedback; retryable failures preserve the question and expose an explicit Retry without a
  duplicate user turn or automatic provider call. Live Chrome timeout injection, real DeepSeek
  HTTP 200, backend 4/4, Ruff, frontend 104/104, lint/typecheck/build and Playwright 12/12 pass.
  Detailed trace #53 meets high-risk tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1628-document-brainstorm-timeout-retry.md`.

- [x] Restore the interrupted Document AI rewrite runtime: the API container was stale and lacked
  the configured DeepSeek credential, causing immediate typed HTTP 503 responses. API and worker
  were recreated from the current `.env`; provider status now reports DeepSeek configured and a
  real request through `localhost:13000` returned HTTP 200 in 9.9 seconds with an explicit
  review-only patch. No application code, database row or document content changed. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1459-restore-document-ai-provider.md`.

- [x] Compile standalone LaTeX as an Overleaf-like PDF Preview (intake #47 / intervention #15 / high-risk story
  `US-LATEX-OVERLEAF-PREVIEW` / DEC-043): debounced source compiles with real bounded XeLaTeX and
  embeds a PDF; typed failures retain the safe-text fallback. Docker runtime, real Chrome CV proof,
  Ruff, 301 backend tests, ESLint, TypeScript, 103 frontend tests, 14-route build and 12/12 document
  Playwright pass. Detailed trace #52 meets high-risk tier 3/3. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1424-overleaf-latex-pdf-preview.md`.

- [x] Render semantic CV macros in safe LaTeX Preview (intake #45 / intervention #14 / normal story
  `US-LATEX-PREVIEW-CV-SEMANTIC-MACROS`): CV sections, role/date/employer rows and tight bullet
  lists are now readable Preview content rather than raw macro source. Live Chrome, ESLint,
  TypeScript, 103 frontend tests, 14-route build and 12/12 document Playwright pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1338-latex-preview-cv-semantic-macros.md`.

- [x] Remove CV body layout syntax from safe LaTeX Preview (intake #44 / intervention #13 / normal story
  `US-LATEX-PREVIEW-LAYOUT-MACROS`): Preview now turns the custom section macro into a heading and
  removes font, color, spacing, minipage and alignment macros before rendering readable text. Raw
  remains untouched. Live Chrome, ESLint, TypeScript, 102 frontend tests, 14-route build and 12/12
  document Playwright cases pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1310-latex-preview-layout-macros.md`.

- [x] Render only LaTeX document body in safe Preview (intake #43 / intervention #12 / normal story
  `US-LATEX-PREVIEW-PREAMBLE`): the browser-safe preview now omits comments, package/font/color
  preamble and other formatting commands; content between `\\begin{document}` and
  `\\end{document}` renders as a clean page. No TeX engine or user-provided subprocess was added.
  Live Chrome, ESLint, TypeScript, 101 frontend tests, 14-route build and 9/9 document Playwright
  pass. Session: `AI_LOGS/SESSIONS/2026-08-04-1246-latex-preview-body.md`.

- [x] Wrap Raw source lines within Document preview (intake #42 / intervention #11 / normal story
  `US-DOCUMENT-PREVIEW-RAW-WRAP`): long LaTeX commands, URLs and unbroken text now wrap in the Raw
  pane, preserving newlines and vertical scrolling without an internal horizontal scrollbar. Chrome
  proof passes at desktop/tablet/mobile; ESLint, TypeScript, 100 frontend tests, 14-route build and
  9/9 document Playwright pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1142-document-raw-wrap.md`.

- [x] Prevent Raw overflow and enlarge the document preview canvas (intake #41 / intervention #10 / normal story
  `US-DOCUMENT-PREVIEW-OVERLEAF`): Raw below `Preview document` now scrolls internally for long
  unbroken lines; Preview uses a larger Overleaf-like white paper canvas and receives 64% width in
  split mode. It stacks safely at tablet/mobile. Live Chrome verified no page-level horizontal
  overflow with 12,000 raw characters across three viewports; ESLint, TypeScript, 100 frontend
  tests, the 14-route build and 9/9 document Playwright pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1136-document-preview-overleaf.md`.

- [x] Require review before every document AI edit and enforce user-requested transformations
  (intake #40 / intervention #9 / high-risk story `US-DOCUMENT-AI-EDIT-REVIEW` / DEC-042): every changed response now
  shows full original/replacement content and waits for explicit Accept or Reject before changing
  the local draft. Exact identical output alone reports no change. The provider prompt applies the
  instruction to the complete selection, repeats it after context, and verifies explicit LaTeX
  output structure. A real DeepSeek request reproduced the old false no-change result and then
  returned a complete standalone LaTeX document with `auto_apply_allowed=false` after the fix.
  Ruff and all 296 backend tests, ESLint, TypeScript, 100 frontend tests, the 14-route build, 9/9
  responsive Playwright and `git diff --check` pass. Session:
  `AI_LOGS/SESSIONS/2026-08-04-1112-reviewed-document-ai-edits.md`.

- [x] Fix live document AI proxy failures and simplify the authoring UI (intake #39 / high-risk
  story `US-DOCUMENT-AI-EDIT-RELIABILITY` / intervention #8 / DEC-041): align Next.js proxy budget
  (125s) above the API AI budget (120s), type malformed provider payloads as 502, localize failure
  classes and offer a user-triggered Retry only for transient errors. Remove duplicated authoring
  descriptions/policy panel, collapse binary upload and Raw/Preview/Song song inspection, and keep
  editor + AI + Create primary. Ruff, 295 backend tests, ESLint, TypeScript, 99 frontend tests,
  14-route build, 9/9 responsive Playwright and a real proxied DeepSeek HTTP 200 call pass. Session:
  `AI_LOGS/SESSIONS/2026-08-03-0026-document-ai-reliability-simple-ui.md`.

- [x] Apply AI edits directly and safely to the local document draft (intake #38 / high-risk story
  `US-DOCUMENT-INSTANT-AI-EDIT` / DEC-040): pre-create and uploaded editable source support native
  selection actions plus a paragraph fallback. Low/medium-risk prose auto-replaces locally with
  Undo/View diff; facts, citations, URLs, code/formulas, semantic-change requests and redacted
  cloud input require explicit review. Full-source revision, selected range and original-text
  checks reject stale responses; provider input is bounded/redacted/structured and creates no
  version or persistence row. Create/Save alone remains durable and triggers the existing RAG
  lifecycle. Ruff, 294 backend tests, ESLint, TypeScript, 94 frontend tests, 14-route build and 9/9
  desktop/tablet/mobile Playwright cases pass. Runtime is healthy on `18000`/`13000`. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-2318-document-instant-ai-edit.md`.

- [x] Unify editable document import with contextual AI brainstorm (intake #37 / high-risk story
  `US-DOCUMENT-UNIFIED-EDITOR-CHAT` / DEC-039): editable UTF-8 Markdown/TXT/LaTeX/rST/AsciiDoc/HTML
  files import directly into the cached `Document content` editor and remain source-editable after
  upload; PDF/DOCX stay binary/read-only. A bounded, redacted, stateless provider route serves chat
  beside both editors. Send never mutates content; Replace selection, Insert at cursor and Append
  are explicit local actions, followed by the existing governed Create/Save flow. The workspace is
  side-by-side on wide screens and stacks without overflow on Windows/tablet/mobile widths. Harness
  fresh proof passes Ruff, 289 backend tests, ESLint, TypeScript, 88 frontend tests, the 14-route
  build and 9/9 Playwright cases; rebuilt runtime health and logs are clean. Detailed Harness trace
  #43 meets high-risk tier 3/3. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-2213-document-unified-editor-brainstorm.md`.

- [x] Fix selected-text actions and Windows chat fit (intake #36 / high-risk story
  `US-SELECTION-ACTIONS-WINDOWS-LAYOUT` / DEC-038): Document Markdown/TXT and Brainstorm messages
  now show a viewport-clamped action popover beside native selection. Document actions reuse the
  explicit proposal/Accept contract; Chat Ask AI/Explain/Summarize only fills a bounded quoted
  composer draft and requires Send. Brainstorm chat is now a focused two-column session/thread
  workspace; duplicated context/knowledge/tool panels are removed, essential metadata is in compact
  header chips, proposal links remain inline, and session horizontal overflow is gone. Topbar labels
  collapse to accessible icons on Windows laptop widths instead of clipping routes. ESLint,
  TypeScript, 84 frontend tests, 14-route build and 15/15 responsive Playwright cases pass, including
  explicit 1366×768 and 1920×1080 fit checks. Rebuilt runtime is healthy on `18000`/`13000`. Session
  log: `AI_LOGS/SESSIONS/2026-08-02-2020-selection-actions-windows-chat-layout.md`. Harness fresh
  proof passed; detailed trace #42 meets high-risk tier 3/3.

- [x] Add human-reviewed inline document editing and automatic scoped RAG (intake #35 / high-risk
  story `US-DOCUMENT-AI-EDIT-RAG` / DEC-037): uploaded Markdown/TXT now supports Raw, Preview and
  Side-by-side editing, F5-safe per-user/workspace/version drafts, selection actions (Improve,
  Shorten, Expand, Fix grammar and custom), persisted proposal comparison and explicit
  Accept/Reject. Manual saves, accepted suggestions and restores create immutable object-backed
  source versions and requeue processing. Successful extraction automatically replaces scoped
  pgvector chunks; draft chunks cannot enter global approved search, RAG failure is independently
  visible/retryable, and source changes clear stale graph evidence before rebuilding. Migration
  `2d4e6f8a0b13` is live after backup. Ruff, 55 focused/285 full backend tests, ESLint, TypeScript,
  83 frontend tests, 14-route build and 9/9 responsive Playwright cases pass; rebuilt runtime is
  healthy on API `18000` / frontend `13000`. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-1925-document-ai-edit-auto-rag.md`.

- [x] Restart the existing local PostgreSQL/API/worker/frontend stack on 2026-08-02 without
  rebuilding images or changing application code/data. It is healthy on API `18000` and frontend
  `13000`; direct/proxied health are `ok`, frontend `/` returns HTTP 200, readiness is `ready`,
  Alembic is at `f8b3d1e6a204 (head)`, and graph verification passes at 45 nodes / 32 edges. Fresh
  startup logs are clean and the unrelated `smart_exam_*` containers were untouched. Session log:
  `AI_LOGS/SESSIONS/2026-08-02-1820-start-local-project.md`.

- [x] Import public ChatGPT shares as one-way governed local forks and correct Markdown/image
  fidelity (intakes #33-34 / high-risk story `US-CHATGPT-SHARED-IMPORT` / DEC-035/036): sanitized
  GFM rendering; bounded current/legacy parser; generated-image tool media without raw tool text;
  anonymous `sediment://file_*` resolution with public-peer/host/MIME/byte validation and transient
  retries; durable object-storage cache; same-origin media endpoint; rollback cleanup; and zero
  media URLs/object keys in provider history. Migration `f8b3d1e6a204` is live. Ruff, 280 backend
  tests, TypeScript/ESLint, 80 frontend tests, 14-route build, 6/6 responsive E2E and a live
  current-format 201 import → 200 cached-PNG round trip pass. Runtime is healthy on API `18000` /
  frontend `13000`; smoke data was removed. Session logs:
  `AI_LOGS/SESSIONS/2026-08-01-2308-chatgpt-shared-local-fork.md` and
  `AI_LOGS/SESSIONS/2026-08-02-0120-chatgpt-import-markdown-images.md`.

- [x] Add direct document authoring with refresh-safe per-user drafts (intake #31 / high-risk
  story `US-DOCUMENT-AUTHORING-CACHE` / DEC-033): Markdown/TXT/LaTeX/reStructuredText/
  AsciiDoc/HTML authoring, safe live source preview, immediate bounded localStorage writes,
  F5 restoration, explicit discard, failure retention and success-only clearing. Creation
  reuses the existing governed upload pipeline. ESLint, TypeScript, 77 frontend tests,
  14-route build, focused backend upload proof and 3/3 responsive Playwright tests pass.
  Session log: `AI_LOGS/SESSIONS/2026-07-30-2338-document-authoring-cache.md`.
- [x] Retire and destructively remove the Training Data Hub (intake #30 / high-risk story
  `US-REMOVE-TRAINING-DATA` / DEC-032): remove `/training`, `/api/v1/training/*`, RBAC patterns,
  ORM/seed/schema/UI/test code and current product commitments; apply migration `e1f7a9c3b205`
  to delete six tables plus one example, one dataset and one membership row. Historical
  migrations/logs remain audit-only. Ruff, 256 backend tests, 71 frontend tests, 14-route build,
  migration reversal/parity, runtime 404/OpenAPI checks and zero-table PostgreSQL proof pass.
  Session log: `AI_LOGS/SESSIONS/2026-07-30-2230-remove-training-data.md`.
- [x] Extend Document workspace with bounded editable document formats and source inspection
  (intake #28 / story `US-DOCUMENT-EDITABLE-FORMATS`): accept PDF, DOCX, UTF-8 TXT, Markdown,
  LaTeX, reStructuredText, AsciiDoc and HTML; validate DOCX OpenXML/expanded size; extract
  canonical AI-readable text; add `GET /documents/{id}/content`; and provide safe Raw, Preview
  and Side-by-side UI modes. Ruff, 257 backend tests, ESLint, TypeScript, 71 frontend tests,
  the 15-route build, rebuilt runtime and live Chrome proof pass.
- [x] Add bounded canonical document text to document-scoped AI chat (intake #29 / high-risk
  story `US-DOCUMENT-SCOPED-CHAT-CONTEXT`) under the already-accepted DEC-019 boundary.
  Existing redaction and final context bounds apply before provider transmission; original bytes,
  raw markup, retention and publish permissions are unchanged. Ten focused graph-chat tests and
  the full 257-test backend suite pass; no live provider received test document content.
  Session log: `AI_LOGS/SESSIONS/2026-07-30-2149-editable-document-workspace.md`.

- [x] Align the primary navigation with the document-workspace task group (intake #27):
  rename the `/documents` desktop/mobile label to `Document workspace` / `Không gian tài liệu`
  and remove `Training data` from both navigation variants. Its initial non-destructive scope was
  superseded by intake #30 / DEC-032. Focused AppShell tests pass 2/2, ESLint and TypeScript pass,
  and live Chrome
  confirms the new label plus zero visible Training data links. Session log:
  `AI_LOGS/SESSIONS/2026-07-30-2123-document-workspace-navigation.md`.

- [x] Restart the existing local four-service stack without rebuilding or changing application
  code/data. It is healthy on frontend `13000` and API `18000`; PostgreSQL is healthy, the worker
  is running, Alembic is at `d8f3b1c6a247 (head)`, and graph verification passes at 45 nodes /
  32 edges. The documented port override remains necessary because another project owns `8000`.
  Session log: `AI_LOGS/SESSIONS/2026-07-30-1957-start-local-project.md`.

- [x] Polish deep-ocean UI/UX across all pages, prioritize graph display, functional
  buttons, spacing/motion. SVG glow/edge-gradient/sheen defs in the D3 renderer, frosted-glass
  zoom control, pill view-switcher/toolbar/breadcrumb, refreshed dashboard hero & cards &
  badges & tables & research tabs & detail/evidence panels, while preserving the accepted
  DEC-014/DEC-015 palette and no API/data behavior. ESLint, tsc, 67/67 Vitest, 15-route
  build and 41/48 Playwright (desktop/tablet/mobile) pass; zero horizontal overflow; the
  one failing E2E case also failed on a clean `git stash` baseline run, so it is a
  pre-existing flake. Session log:
  `AI_LOGS/SESSIONS/2026-07-30-1055-ui-ux-graph-polish-deep-ocean.md`.

- [x] Make Discord link intake explicitly zero-command and add authorized same-channel
  pinning (owner correction #5 / intake #26 / story `US-DISCORD-AUTO-SUBMIT-PIN` /
  DEC-031). Ordinary allowlisted link/PDF messages auto-collect; `/submit` is optional.
  `/pin message_id:<id>` requires `PIN_MESSAGES` for caller and bot, never searches another
  channel, is idempotent and adds only a bounded Discord audit reason. 55 gateway tests,
  Ruff, focused graph-gap backend proof, Compose, discord.py 2.7.1 image and actual
  auto-intake/pin callback smoke pass.
- [x] Add normal bot commands and user guidance to the Discord gateway (intake #25 / story
  `US-DISCORD-BOT-COMMAND-GUIDE`): allowlist-gated `/help`, `/guide`, `/sources`, `/ping`,
  `/submit`, `/status`; bilingual source/limit/review/graph/gap copy; discoverable presence
  and mention hint; safe command-error response; and correct global-to-guild command sync.
  43 gateway tests, Ruff, Compose config, production image build and a credential-free 6/6
  command-tree smoke pass.
- [x] Write an executable Vietnamese Discord bot test runbook (intake #24 / story
  `US-DISCORD-BOT-TEST-RUNBOOK`): Discord application and intent setup, least-privilege
  credentials, local stack startup, article/multi-link/duplicate/PDF/Reel/allowlist/slash-command
  cases, receipt/graph/gap proof, expected reactions, troubleshooting and cleanup. Markdown/static
  checks, Compose config, 36 gateway tests, the focused backend graph-gap integration proof and
  the Discord image build pass. Live guild execution remains owner-operated because it needs
  external credentials.
- [x] Extend the Discord gateway with guarded auto-ingest and channel knowledge-gap alerts
  (intake #23 / story `US-DISCORD-GAP-ALERTS` / DEC-030). Discord URL items now request
  `auto_approve=true` by default; complete high-confidence links become approved research and
  relationship-graph nodes, approval refreshes persisted low-coverage gaps, scoped receipt reads
  expose only related active gaps, and the bilingual reply reports them without expanding the
  bot's `intake:submit` / `intake:read-own` scopes. 252 backend, 36 gateway and 67 frontend tests
  pass; full lint and the Discord image build pass. Real guild delivery still needs owner secrets.
- [x] Add and simplify the shared footer on every Research System workspace route (intakes #21-22 /
  story `US-WEB-SHARED-FOOTER` / correction intervention #4). The final dark bar keeps only the
  product name, Research/Sources/Knowledge graph links and copyright, with semantic shell coverage
  and desktop/tablet/mobile no-overflow proof. 67 frontend tests and the 15-route build pass.
- [x] Sweep frontend, backend and database for defects the completion goal's tests could not
  see (intake #20 / story `US-FULLSTACK-DEFECT-SWEEP`). Seven fixed: `alembic upgrade head`
  failing on SQLite because a foreign key was added outside batch mode; two URLs redirecting
  to one page crashing the worker on the unique URL index and retrying to exhaustion; five
  foreign keys with no index, including the `research_tags` join table; duplicates recorded
  before `duplicate_of_id` existed never being backfilled; backlog counts returned as floats
  so a caller would render "0.0 sources are waiting"; an unknown status filter answering
  `200 []` instead of refusing a typo; and an E2E suite that raced six workers against one
  backend. Migrations `c7e2a5b8d431` and `d8f3b1c6a247`; head is now `d8f3b1c6a247`.
- [x] Build the Discord intake gateway (`apps/discord-bot`, Compose profile `discord`):
  allowlist closed by default, multi-URL and PDF attachments persisted before async
  processing, idempotent on the Discord message ID, bilingual reactions and per-item
  replies, `/submit` and `/status`, scoped service account limited to `intake:submit` and
  `intake:read-own`, plus `GET /api/v1/intake/receipts?occurrence_ref=` confined to the
  caller's namespace. 33 gateway tests run without Discord or a network. Goal D1-D6.
- [x] Finish the graph workspace: empty-branch guidance, no expand affordance on empty
  boards, view-appropriate filters, search-to-focus across the whole tree, keyboard-
  reachable nodes with announced selection, one translated colour/label system, and the
  removal of the dead Cytoscape renderer and dependency. Three-viewport Playwright proof
  found and fixed the hierarchy failing to re-fit on resize, which left 23 node labels off
  the canvas on mobile. Goal C6-C12.
- [x] Add a secret-safe AI provider preflight (`?preflight=true`) with a 60-second cache and
  a UI panel. It immediately showed that the live OpenAI key does not answer while DeepSeek
  and Mistral do. Goal E2.
- [x] Be a well-behaved reader: per-host request spacing, optional `robots.txt` support that
  treats an unreachable robots file as permitting, and conditional GET so an unchanged page
  is not downloaded again. Goal B10, B13.
- [x] Fix the intake review backlog, duplicates and projection staleness: a backlog
  endpoint with a discoverable auto-approve threshold, bulk approve/reject reporting each
  outcome, `duplicate_of_id` (migration `b6d9f1a3c527`) so a duplicate of an unpublished
  original inherits its research record instead of being stranded, rejected sources no
  longer blocking re-collection, and `GET /api/v1/graph/projections` reporting which
  derived copies are behind the canonical graph. Goal A2, A4, A5.
- [x] Reconcile relationship-view taxonomy against canonical ontology labels and aliases so
  one concept keeps one identity across both graph views. Goal A3.
- [x] Make the hierarchy navigable at any depth: focus-based drilldown, position-correct
  breadcrumb, a browse action hidden on leaves, explicit "showing N of M" paging with a
  Show more control, and header metrics that describe what is drawn. Goal C1-C5.
- [x] Close the link-intake-to-hierarchy gap: approving a link now proposes canonical
  placements under the eleven pillars through the same governed change-set path uploaded
  documents use, evidence-backed and human-gated. Proven live on `arxiv.org/abs/2210.03629`
  with 16 valid mutations and 0 errors. Intake #19 / story `US-COMPLETION-INTAKE-TO-GRAPH`.
- [x] Make link extraction failures specific and actionable: browser request identity,
  per-host header overrides, content-type aliases refused before download, real charset
  resolution, bot-challenge and consent/paywall detection, split retry layers, a
  peer-address SSRF check, and 31 bilingual error titles with remediation hints replacing
  "The source could not be processed". 202 backend and 35 frontend tests pass.
- [x] Give the worker a diagnosable failure log: exception type and code location without
  exposing exception messages, plus bounded backoff on repeated loop failures.
- [x] Export the verified Business AI Agents completion/gap report to
  `Docs/Business AI Agents Project Status Report.md`, covering every original requirement, current
  evidence, owner-acceptance blockers, OpenAI/DeepSeek status and production backlog (intake #18).
- [x] Replace the rejected external board branch with compound/folding boards: keep the root and
  sibling boards visible, expand the selected `SystemPillar` into a bounded container, lay every
  direct child inside it, hide internal containment edges and collapse from the same header.
  Intake #17 / story `US-GRAPH-COMPOUND-BOARDS` / trace #26 pass 32 frontend tests, TypeScript,
  the 15-route build, 30 enabled full E2E cases plus focused three-viewport Harness verification
  and live Chrome proof on the real 33-child board.
- [x] Implement the now-superseded external-branch board drilldown: root + eleven collapsed
  system boards, localized node counts, single-click board opening, direct children only, breadcrumb
  return and multi-column layout for large board node lists. Intake #16 / story
  `US-GRAPH-BOARD-DRILLDOWN` pass 32 frontend tests, production build, 15 cross-viewport E2E cases
  and real rebuilt-runtime visual/console proof.
- [x] Complete live selected-provider chat proof through DeepSeek `deepseek-v4-pro`: secret-safe
  preflight ready, bounded graph tools exercised, broad-turn loop limit handled safely, ungrounded
  proposal rejected, and document-scoped chat created review change set
  `5759af2f-4685-4cfa-b360-39d7981a1fa4` with one evidence-supported valid mutation, zero errors or
  warnings and no canonical apply.
- [x] Correct the main graph to the owner-provided parent/child sketch: hierarchy-first
  left-to-right cards, curved branches and visible connection ports; root-to-eleven-pillar overview;
  ancestor-preserving descendant focus without sibling leakage; relationship network retained as a
  secondary mode. Intake #15 / story `US-GRAPH-HIERARCHY` are complete with 41 backend tests,
  29 frontend tests, production build, 15 cross-viewport E2E cases and rebuilt runtime proof.
- [x] Restart the existing four-service Research System stack on 2026-07-25 without rebuilding;
  preserve PostgreSQL/object data; verify API `18000`, frontend `13000`, direct/proxied health,
  enabled features, migration head, valid graph readiness and clean startup logs without touching
  `smart_exam_*`.
- [x] Implement the accepted temporary DeepSeek graph-chat path without weakening governance:
  provider-neutral selection, non-thinking Chat Completions tool/result translation, server-side
  schema validation, generic secret-safe preflight, API-only secret overlay, bilingual UI provider
  selection and reversible OpenAI switchback. Intake #14 and decision 0016/DEC-029 hold the contract;
  168 backend tests, 28 frontend tests, production build and 30 E2E cases pass.
- [x] Harden the remaining Graph v2 acceptance gate with an API-only managed OpenAI secret overlay,
  a minimal `store=false` operator preflight that never prints secret/provider content or ID values,
  and an executable Harness verifier that requires runtime/graph/OpenAI proof plus Linh's completed
  walkthrough and accepting decision. Full proof passes 165 backend tests, 28 frontend tests and 30
  desktop/tablet/mobile E2E cases before correctly failing on the still-rejected HTTP 401 credential
  and unchecked human acceptance markers.
- [x] Implement and verify the accepted source-neutral intake boundary: additive receipt/item and
  hashed scoped-service-account schema, deterministic no-reprocess legacy backfill, multi-URL replay
  and repeated-occurrence provenance, durable document read-back/cleanup, namespace authorization,
  legacy dual-write, concurrent convergence, PostgreSQL backup/restore/runtime rollout and real
  MinIO proof. Harness intake #13 / story `US-INTAKE-RECEIPTS-IMPLEMENT` / detailed trace #17 are
  complete; 163 backend tests, 28 frontend tests and 30 desktop/tablet/mobile E2E pass. Discord was
  deliberately not started.
- [x] Specify the source-neutral intake occurrence/receipt model before Discord: separate receipts
  and URL/document items from processing aggregates, define message+normalized-URL idempotency,
  repeated provenance, multi-item/PDF durability, auth/privacy/audit, additive backfill and Gate D
  criteria; complete Harness intake #12, decision 0015/DEC-028, story and static verifier.
- [x] Add the separately authorized legacy-object migration path: dry-run aggregate inventory,
  explicit copy-only confirmation, local/remote byte and SHA-256 verification before per-object
  reference commit, bounded audit evidence, repeat/verify modes, no delete path, 150 backend tests,
  a clean read-only main plan for 3 objects / 2,822 bytes and disposable real-MinIO proof.
- [x] Implement and verify Gate C search projections: approved-only atomic Meilisearch staging/swap,
  real Mistral `mistral-embed` vectors in pgvector `vector(1024)`, owner-only rebuild, explicit
  fail-visible provider selection, canonical hydration, migration/image/secret/profile wiring, 141
  backend tests and real repeat/parity/stale-prune/read proof with 3 documents / 9 chunks.
- [x] Implement and verify the optional idempotent Neo4j projection for relationship/hierarchy
  views: owner-only atomic rebuild, composite constraints, parameterized batching, stale pruning,
  bounded query/path/cluster reads, typed fail-visible errors, internal-only digest-pinned Compose
  profile, 130 API tests, real-server parity and 30 serial Playwright passes.
- [x] Add bounded source enrichment: optional shared PDFium/Tesseract OCR for URL/upload scans,
  optional SSRF-guarded Browserless article rendering, researcher-supplied timestamped public Reel
  transcripts with reprocessing/non-leaking audit/API behavior, migration `0b7d2e4f6a18`, 125 API
  tests, 28 web tests, 30 local E2E, image builds and actual OCR/Browserless runtime smoke.
- [x] Add local production-boundary authentication and managed-secret support: Argon2 credentials,
  hashed opaque sessions, HttpOnly/SameSite cookies, CSRF, owner/researcher/viewer API enforcement,
  authenticated audit attribution, operator/user administration, production fail-closed settings,
  `/run/secrets` precedence, Compose overlay, bilingual role-aware login UX, 118 API tests, 26 web
  tests, migration/build/Compose proof, 27 local E2E and six enabled-auth E2E cases.
- [x] Add production-safe application observability: validated/generated request correlation,
  strict JSON API/worker logs, raw URL-log suppression, bounded HTTP/provider/rate-limit/job metrics,
  secure-default bearer-protected `/metrics`, operator docs, 104 backend tests, 27 E2E cases,
  image/runtime scrape proof and disabled-default restore.
- [x] Add reversible MinIO/S3-compatible document attachment storage: scheme-routed remote keys,
  legacy local reads, safe server-only credentials, bounded spool/streaming, transient worker retry,
  SDK/image proof, disposable live MinIO and rebuilt local round trips, 96 backend tests and 27 E2E.
- [x] Harden structured document-graph reliability with one bounded same-provider Pydantic recovery,
  no cross-provider/mock fallback, prompt version v2, safe recovery logs, three deterministic retry
  tests, all 88 backend tests, 27 Playwright cases and a live first-pass Mistral graph with 20
  supported nodes/14 valid edges.
- [x] Complete the engineering-assisted non-chat Graph Intelligence v2 walkthrough: real Markdown upload, DeepSeek evaluation/39-node isolated graph, evidence and hierarchy inspection, edit/reject/approve/apply/history with 65 accepted and one rejected mutation, valid 45-node/32-edge canonical graph, dense-graph row-wrapping fix, current runtime rebuild, 26 focused backend tests, 24 frontend tests and 27 E2E cases. Final OpenAI chat and product-owner decision remain open.
- [x] Re-verify the existing Repository Harness setup, bootstrap it idempotently, confirm CLI `0.1.17`, record intake #2, and create an active completion goal aligned with Graph v2 acceptance, Gate C, projection upgrades and the deferred Discord adapter.
- [x] Install Repository Harness `v0.1.17` with the existing AI handoff workflow preserved; bootstrap schema 13 and verify intake #1 plus drift audit entropy `0/100`.
- [x] Complete Graph Intelligence v2 Phase 6 engineering: 30-item release evaluation with 1.00 routing precision/top-three placement recall/near-duplicate recall, production placement fallback and duplicate review signals, server-enforced rollout flags, rate/timing controls, graph invariant readiness, SQLite/PostgreSQL migration parity, backup/restore drill, operations/acceptance docs, rebuilt runtime, 85 backend tests, 23 frontend tests and 27 E2E cases.
- [x] Complete Graph Intelligence v2 Phase 5: local chat session/message persistence, six bounded scopes, provider-neutral orchestration, strict OpenAI Responses read/propose tools with redaction and `store: false`, draft change-set linking, bilingual responsive `/chat`, typed failure recovery, migration `e9f5c2a7d104`, rebuilt PostgreSQL runtime, 78 backend tests, 23 frontend tests and 27 desktop/tablet/mobile E2E cases.
- [x] Complete Graph Intelligence v2 Phase 4: exact canonical/alias and bounded similarity candidates, typed document mapping proposals, evidence/duplicate/cycle/edge validation, per-mutation edit/accept/reject, transactional idempotent apply, compensating change sets, bilingual graph diff UI and rebuilt PostgreSQL runtime verification.
- [x] Complete Phase 3 processing and document graph: leased/retryable worker, bounded extraction, provider-neutral paper evaluation, persisted deterministic routing, isolated nodes/edges, verbatim evidence validation, analysis APIs and responsive graph/evaluation UI.
- [x] Implement the Phase 3 scoring/upload foundation: 30-paper versioned gold set, deterministic hard gates/score/routing, bounded local PDF/Markdown/text object storage, draft research/workspace persistence, document upload/list/detail/download API, bilingual `/documents` UI and responsive verification.
- [x] Implement Graph Intelligence v2 Phase 2: ontology root/breadcrumb APIs, lazy one-hop hierarchy queries, stable layered D3 layout, relationship/hierarchy switcher, preserved selection, breadcrumb/child navigation, four node-detail tabs and desktop/tablet/mobile verification.
- [x] Accept the Graph Intelligence v2 implementation defaults and implement the Phase 1 backend foundation: additive ontology/evidence/change-set migration, deterministic root plus eleven pillars, placement/cycle validation, ontology read/search/children APIs, optional graph v2 fields, hierarchy query mode and regression tests.
- [x] Convert the Graph Intelligence v2 brainstorm into a detailed implementation plan covering goals/non-goals, architecture, eleven-pillar ontology, paper-fit rubric, document graph workspaces, hierarchy/relationship views, graph change sets, provider-neutral OpenAI-compatible chatbot, data model, APIs, frontend/backend modules, worker stages, validation, security, testing, phased estimates, acceptance criteria and open decisions.
- [x] Fix the `/graph` `Can't resolve 'd3'` runtime failure by detecting and synchronizing incomplete dependencies in the persistent frontend `node_modules` volume before Next.js starts; verify `d3@7.9.0`, HTTP 200 from `/graph`, clean graph compilation, TypeScript, and 12/12 frontend tests.
- [x] Rebuild the current API, worker, and frontend Docker images and recreate the core stack on 2026-07-17 at 14:28 +07; preserve PostgreSQL data; verify all four services are up, PostgreSQL is healthy, direct/proxied health and frontend return HTTP 200, and fresh logs are clean without touching the optional Ollama bridge or `smart_exam_*`.
- [x] Restart the existing four-service Research System stack on 2026-07-17 at 14:10 +07 without rebuilding; verify PostgreSQL health plus HTTP 200 from direct API health, frontend root, and proxied API health; confirm clean startup logs without starting the optional Ollama bridge or touching `smart_exam_*`.
- [x] Replace Cytoscape.js with D3.js for Knowledge Graph visualization: force-directed layout, custom node shapes, hover effects, zoom controls, drag interaction, and responsive design.
- [x] Optimize Knowledge Graph UI: smaller nodes (26px), improved font (11px), hover/selected effects, zoom controls, collapsible filters/legend, better layout parameters, and responsive design.
- [x] Document the “Xử lý nguồn” URL-intake pipeline in Vietnamese with a Mermaid flowchart, status/review state machines, retry and typed-error paths, adapter behavior, approval semantics, and code ownership map.
- [x] Start the existing Research System Docker Compose stack on frontend `13000`/API `18000` on 2026-07-17, verify direct/proxied health and the frontend root, and confirm clean fresh startup logs without touching `smart_exam_*`.
- [x] Audit DeepSeek and the complete live intake pipeline across GitHub/article/paper/PDF/Facebook/error/dedup/review/publish/search/graph; fix DataCite DOI fallback and PostgreSQL JSON search; harden retry/logging; pass 43 backend, 12 Vitest and 12 Playwright tests plus clean rebuilt-runtime checks.
- [x] Remove the runtime AI mock provider from backend, intake schema, UI, Compose/env defaults and current docs; activate configured Mistral, keep deterministic behavior test-only, rebuild the stack and verify mock submissions are rejected.
- [x] Rebuild and start the four-service local Docker stack on frontend `13000`/API `18000`, then verify direct health, proxied health, frontend HTTP 200, PostgreSQL health, and clean startup logs on 2026-07-17.
- [x] Audit and retheme the complete frontend with an accessible deep-ocean navy/teal/indigo palette, including graph/icon styling and a bounded desktop intake queue.
- [x] Add an optional bounded host-Ollama bridge and verify the already-installed `qwen3.5:4b` model without downloading images or models.
- [x] Fix Ollama structured output, expose provider reachability, map provider failures to typed safe errors, and add regression tests.
- [x] Probe Mistral, DeepSeek and local Ollama live, then run the GitHub/article/PDF/Facebook Reel source matrix using only those providers.
- [x] Complete final backend/frontend/build/Compose/runtime/log/artifact audit with 38 Pytest, 12 Vitest and 12 Playwright tests passing.
- [x] Restart and verify the local Docker runtime on frontend 13000/API 18000 without affecting the unrelated Smart Exam containers.
- [x] Rebuild every Research System frontend route using `/home/linh/smart-exam-ai` as the visual reference.
- [x] Add self-hosted Inter, Smart Exam color/surface/radius tokens, sticky topbar/pill navigation and reference-style dashboard sections.
- [x] Verify dashboard, intake, research list/detail, search, graph, gaps, collector and training visually on desktop and tablet.
- [x] Extend Playwright to desktop/tablet/mobile with all-route hydration, exact visual token, untranslated status, multi-source interaction and overflow coverage.
- [x] Prevent stale host `NEXT_PUBLIC_API_URL` values from bypassing the local Compose frontend proxy.
- [x] Reproduce and fix the reported post-rebuild runtime and UI failures using live browser console/network checks and interaction flows.
- [x] Implement the staged, typed and bounded URL-to-knowledge pipeline for GitHub, Facebook, papers, direct PDFs and generic websites.
- [x] Add direct PDF text-layer extraction with explicit scanned-PDF limitation handling.
- [x] Replace the AI/neon visual treatment with a neutral responsive productivity UI and multi-link per-row workflow.
- [x] Add unit/integration coverage plus Playwright desktop/tablet hydration, submission, console/network and overflow tests.
- [x] Verify automatic migrations, health and real URL ingestion from a clean Compose project with fresh volumes.
- [x] Rebuild Docker images and recreate the full project stack on ports 18000/13000 after the graph/source/workflow refactor.
- [x] Add normalized GitHub/article/Reel/PDF source adapter contract with safe Reel/PDF pending states.
- [x] Add typed, validated and bounded graph API contract with PostgreSQL/mock/Neo4j provider boundary.
- [x] Refactor graph UI into lifecycle-safe Cytoscape components, filters, legend, details, evidence and neighbor expansion.
- [x] Add research review tabs plus reject/resubmit workflow while mapping approved to the published projection state.
- [x] Add backend graph/source/workflow tests and frontend graph state/lifecycle/dedup tests.
- [x] Fix same-URL intake resubmission to honor the newly selected provider and show clear UI feedback.
- [x] Add Mistral strict structured-output provider with environment-only key configuration.
- [x] Move URL intake processing to a PostgreSQL-backed worker with leases, exponential retry and dead-letter/manual retry.
- [x] Standardize repository layout as `apps/api` and `apps/web`, including runtime commands and architecture docs.
- [x] Phase 0 specification.
- [x] Local foundation and Docker Compose.
- [x] Research CRUD/lifecycle/version/comments/tags/relations/attachments.
- [x] Research frontend library/detail/editor.
- [x] Search and related research.
- [x] Knowledge graph MVP.
- [x] AI enrichment with real-provider adapters, test-boundary deterministic coverage, provenance and embeddings.
- [x] RSS collector and review queue.
- [x] Training Data Hub foundation and JSONL export.
- [x] Seed data, tests, lint, build, dependency audit and docs.
- [x] Phase 8 foundation: low-coverage detector, persistent gap lifecycle, gap workspace, deep-research draft and human approval gate.
- [x] Configurable Docker CORS override and isolated frontend `.next` named volume.
- [x] Source-neutral URL intake with SSRF guard, extraction, dedup, classification, review and publish.
- [x] Ollama/OpenAI/DeepSeek/Gemini/OpenRouter/Mistral provider registry without exposing API keys or offering an in-process fake fallback.
- [x] Typed graph ontology, clusters/stats and Cytoscape.js interactive frontend.
- [x] Persistent EN/VI shell and primary dashboard/intake/graph translations.
- [x] EN/VI translation coverage for research, search, collector, gap, training, detail and form workflows.
