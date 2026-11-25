# Task Board

Cập nhật 2026-11-25. Trạng thái hiện hành ở [HANDOFF](HANDOFF.md). Bảng trước khi hoàn tất local models
giữ tại [archive](ARCHIVE/2026-11-18-before-deployed-local-models-TASKS.md).

## Now

- [x] Intake 39 (Antigravity, 2026-11-25): sửa `stage_searching` duyệt hit theo hạng trước
  (`rank-first round-robin`), `EXTRACT_PASSAGE_MAX_CHARS = 5200`, `MAX_EXTRACT_SOURCES_PER_BATCH = 4`,
  `EXTRACT_TASK` v3 (`research-extract-v3-grounded-entities`). Harness verify đạt (API 939/bot 56/
  web 236 + eslint/tsc + 3 Compose config). Đo lại 8 câu (`r2`) hoàn tất 16/16, 0 thiếu usage:
  **16/16 lượt đạt 5/5 góc nhìn và 100% trích dẫn**, **−46,3% token (897.992 → 481.846)**,
  `entity_recall` TB tăng **0,400 → 0,450** (+12,5%); chỉ còn 2 điểm dao động 1 thực thể từng câu
  (`q6-roi`, `q8-sme-vietnam`). Artifacts: `docs/evaluations/research-agent/2026-11-25-r2-*`.
- [x] Intake 38 (Antigravity, 2026-11-25): thêm `select_relevant_passages` và cờ `passage_filter`
  (`True` ở `optimized`, `False` giữ baseline ở `reference`/`naive`; 5.000 ký tự/nguồn, tối đa 6
  nguồn/lô) + làm rõ `WRITE_TASK` (`research-write-v3-all-perspectives`). Đo 8 câu (`r1`) giảm
  −51,8% token, −30,4% thời gian; artifacts: `docs/evaluations/research-agent/2026-11-25-*`.
- [ ] Đóng nốt cổng `entity_recall` từng câu của `US-OPTIMIZATION-PROGRAM` (chỉ còn 2/8 câu dao
  động 1 thực thể dù trung bình `optimized` 0,450 > `reference` 0,400 và 16/16 lượt đạt 5/5 góc
  nhìn + 100% trích dẫn). Chờ quyết định của Linh về đợt đo lại hoặc chốt chính sách đánh giá.
- **Bàn giao cho Antigravity.** Đọc [phiên bàn giao](SESSIONS/2026-11-25-1324-antigravity-handoff.md)
  và [phiên tối ưu mới nhất](SESSIONS/2026-11-25-1340-research-passage-optimization.md).
- [x] Intake 36: rút gọn `.env.example` còn 58 dòng, cập nhật vị trí tra cứu mặc định trong
  README và kiểm tra cấu hình Compose trước/sau khớp ở bốn trường hợp.
- [x] Intake 35: ưu tiên góc nhìn có trích đoạn hỗ trợ, bổ sung mục từ nhận định đã kiểm chứng
  và ghi chẩn đoán theo góc nhìn. Mẫu Codex `q1-market-size` đạt 5/5 góc nhìn và 100% độ phủ trích
  dẫn ở cả hai biến thể. Harness verify đạt (API 935, web 236), worker local đã nạp mã mới.
- [x] Intake 34: kiểm tra variant/corpus ở cổng KPI và thêm cờ dừng sớm khi provider lỗi.
  Harness verify đạt (API 933, web 236). Preflight Codex đạt, hai biến thể chạy xong một câu
  trên database tách biệt.
- [x] Intake 33: dọn journal lưu trữ theo mức 400 MiB, thu hồi 807,8 MiB. Tổng journal còn
  398 MiB, journald active và phân vùng `/` còn 9,74 GB khả dụng.
- [x] Intake 32: dọn cache cơ sở dữ liệu Trivy của Deka, thu hồi khoảng 1,63 GB trên `/home`.
- [ ] Dọn cache `uv` (~1,1 GiB) khi tiến trình `uv`/Python của Codex đóng cache. Hai lệnh
  chuẩn `uv cache clean` và `uv cache prune` đang chờ khóa.
- [x] Intake 31: gỡ 7 image không có container tham chiếu của Deka, Smart Exam và Cineforge.
  Thu hồi 3,59 GB trên `/`, còn 8,90 GB khả dụng. Container, volume và kiểm tra HTTP đạt.
- [x] Intake 30: đọc dung lượng các thư mục root, dọn cache APT, Snap cũ và BuildKit cùng ba
  image tải lại được. Phân vùng `/` còn 5,31 GB khả dụng. API và frontend vẫn trả 200.
- [x] Intake 29: build image Docker API/worker và frontend standalone với tag `local-build-20261125`.
  Hardening, OCR/LaTeX và migration đạt. Smoke test các image trên mạng/DB tách biệt qua API,
  worker, trang đồ thị, JavaScript và proxy xác thực đều đạt.
- [x] Intake 28: dọn toàn bộ cache BuildKit có thể thu hồi trên builder local `default`.
  Thêm 763,5 MiB khả dụng, cache còn 0 B. Danh mục image/container/volume khớp trước và sau.
- [x] Intake 26: audit lại thay đổi của intake 25, khôi phục build frontend, màu dây nối SVG và
  vị trí nút có quan hệ phân cấp phụ trong bảng trụ cột. Local `:13000` healthy. API 925, bot 56,
  Vitest 236, Playwright 55 đạt (2 lượt desktop-only bỏ qua), 9 ca đồ thị đạt khi chạy lại với
  kiểm tra bàn phím/cảm ứng. Migration khứ hồi và 21 ca PostgreSQL đạt trên container tách biệt.
- [x] Intake 27: gỡ hai image dự án không dùng, phân vùng Docker từ 0 lên 437 MiB khả dụng.
  Database thử trên PostgreSQL local chạy migration khứ hồi và 21 test đạt. Backup mới lúc 09:46
  đã verify-only, API/worker chạy lại và UI local trả 200.
- [x] Intake 24: sửa nút Nhãn trong đồ thị phân cấp và sơ đồ hệ thống, bỏ ghim khi nhấp chọn,
  giữ card và mức zoom khi dữ liệu đổi giữa lúc kéo, trả vị trí cũ khi hủy chạm.
  Bản local `:13000` healthy, 232 Vitest và 22 Playwright đạt, 2 lượt desktop-only được bỏ qua.
- [x] Intake 23: sửa 5 lỗi sau audit Weave. Production local `:13000` đã nạp code mới.
  Vitest 232, lint/typecheck/build, Playwright 19 đạt (2 bỏ qua theo cấu hình). Chờ nghiệm thu UI.
- [x] `US-WEAVE-GRAPH-CANVAS` (intake22,2026-11-20): biểu đồ node theo phong cách Weave — card bo
  góc/accent/badge mono, edge bezier, dark dot-grid / light giữ giấy, kéo thả tự do mọi layout +
  "Sắp xếp lại". vitest232, e2e graph16 passed/3 viewport, build sạch, story complete pass.
  Runtime:13000 đã build lại; **chờ Linh nghiệm thu UI**.
- [x] `US-SECOND-AUDIT-REMEDIATION` (intake21,2026-11-20): sửa đủ12 phát hiện; regression 42+17+38+67
  ca đạt; full proof `verify_second_audit_remediation.sh` exit 0 (API920/web226/bot56); PostgreSQL
  migration smoke + 21 guard test PG đạt; runtime refresh fencing + health 200; backup timer cài lại
  guard `.restore-*`; `harness-cli story complete` = pass.
- [x] Sửa phân loại lỗi `AI_RESPONSE_INVALID` (intake #20): `BridgeProtocolError` + `_llm_failure_code`
  (401/403/429 → `AI_PROVIDER_AUTH_FAILED`/`AI_PROVIDER_RATE_LIMITED`); 9 regression test; API 818
  passed. Đã restart api/worker.
- [ ] Mistral generation: Large403 `tier_not_allowed`, Medium/Small429; embedding vẫn hoạt động.
  Cần hạn mức/tier phù hợp trước khi chọn Mistral sinh nội dung; không đổi mặc định để né lỗi.
- [ ] Operator cài model thật (Ollama hoặc LM Studio) trên máy chủ/tunnel, đặt env và xác nhận chat/JSON
  end-to-end; ghi evidence riêng, không dùng fixture. Sau đó Linh nghiệm thu UI local models.
- [x] CI `.github/workflows/ci.yml` đã đẩy lên `origin/feature/research-system-mvp` (`bf5c69d`,
  intake #40 sửa `python -m pytest`): GitHub Actions **`ci` run `45581065933` SUCCESS** (5/5 job:
  API, Discord bot, Web, PostgreSQL migrations/parity, Compose) và **`security` run `45581066073`
  SUCCESS** (2026-11-25).

## Blocked / Needs Owner Inputs

- [ ] Gemini: cung cấp key qua `.env`/secret; sau đó mới chọn embedding Gemini và re-index theo 0050.
- [ ] OpenAI: thay key không hợp lệ nếu muốn dùng; chạy `verify-openai` trước khi chuyển mặc định.
- [ ] Claude: kiểm tra tài khoản/billing do native probe đang lỗi; Codex và agy hiện dùng được.
- [ ] ChatGPT plan: user tự đồng ý OAuth tại `/account`; bản web cần client ID/secret/redirect hợp lệ.
  Mã/tests có sẵn, chưa có bằng chứng consent thật. Không đăng ký hay chấp thuận thay user.
- [ ] Team HTTPS: user chưa có tên miền; cần tên miền/địa chỉ HTTPS, cấu hình `.env.team` và đủ đĩa.
  Chưa bật team. Cấu hình/runbook đã sẵn; không tạo domain/client ID giả.
- [ ] Offsite backup: timer local đã chạy; cần đích sao chép ngoài máy và quyền truy cập thực.
- [ ] Linh nghiệm thu Graph v2 theo `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`,
  xem change set `5759af2f-4685-4cfa-b360-39d7981a1fa4` và link set
  `42ae7795-280e-4ee1-8525-2462cc061074` trước khi quyết định apply.
- [ ] Linh nghiệm thu trải nghiệm UI tiếng Việt trên dashboard/intake/research/graph.
- [ ] Nếu hết nhu cầu điện thoại: user chọn tắt quick tunnel/gate; hiện vẫn bật, có basic auth + app auth.

## Later

- [ ] Chuẩn hóa khóa tag/ontology giữ dấu tiếng Việt (hiện `máy`→`m-y`, nhãn chỉ khác dấu bị gộp);
  cần migration tính lại khóa + gap keys.
- [ ] Tiêu thụ hoặc bỏ `outbox_events` (đang chỉ ghi); cân nhắc tự cập nhật bản chiếu pgvector khi duyệt.
- [ ] Rate limit/metrics dùng chung (Redis hoặc PostgreSQL) nếu chạy nhiều máy/nhiều worker.
- [ ] Quyết định phạm vi chuyển sang OpenRouter free (2026-10-12 đã đánh giá): chỉ đổi `AI_PROVIDER`
  (không code) hay thêm graph chat/embedding OpenRouter (cần code, embedding cần khớp 1024 chiều hoặc
  migration + re-index). Session: `AI_LOGS/SESSIONS/2026-10-12-0945-openrouter-free-assessment.md`.
- [ ] Decide whether a future layout-faithful DOCX/PDF authoring/export engine is needed. Current
  post-upload editing safely versions AI-readable UTF-8 derivatives and preserves the original binary,
  but deliberately does not round-trip Office/PDF layout.
- [ ] Decide whether to batch-rebuild RAG for the three legacy workspaces backfilled by migration
  `2d4e6f8a0b13`; they are visible as `pending` and can be rebuilt individually without re-upload.
- [ ] Extend background processing to scheduled collectors and add optional Redis transport.
- [ ] Add more collector adapters after RSS is validated.
- [ ] Add deployment-owned telemetry retention/alerts, backup and remaining production hardening.
- [ ] Run the Discord gateway against a real Discord application. The code, image and Compose profile are
  complete; only a bot token and an allowlisted server are missing, and both are the owner's to provide.
- [ ] Persist HTTP validators between submissions so conditional GET saves a download across jobs, not
  only within one fetch. Needs a schema column.

## Done — 2026-11-19 (audit remediation)

- [x] Toàn bộ sửa đề xuất audit (writer nguyên văn claim, usage/eval fail-inclusive, manifest/corpus
  cố định, local model che khóa, deadline DNS, backup lock chung, lockfile frontend, CI Node22/PG).
- [x] Paired eval 8 câu reference/optimized hoàn tất; artifacts chỉ số/hash + comparison đã lưu
  `docs/evaluations/audit-remediation/`; kết luận quality gates KHÔNG ĐẠT được ghi nhận tường minh.
- [x] Proof cuối `verify_audit_remediation.sh` exit 0 (API809/web226/bot56); api/worker restart
  nạp DNS/usage cuối; `harness-cli story complete US-AUDIT-REMEDIATION` = pass.
- [x] Mistral live probe: models200, embedding 1024 chiều; generation chặn bởi tier/rate limit.

## Done — 2026-11-18

- [x] `US-DEPLOYED-LOCAL-MODELS` implemented: Ollama + OpenAI-compatible local cho chat/JSON; inventory,
  probe, model pinning, fail-closed tool validation, RBAC/CSRF/rate limit, secret server-side.
- [x] Compose base/team: env local model dùng chung api/worker; `local-openai-bridge`; profile `local-ai`;
  team đóng gói bridge, không mount source. `.env.example` + README runbook cập nhật.
- [x] API full pytest, ruff, web vitest/typecheck/lint xanh; Playwright local models 6/6 trên runtime thật.
- [x] Recreate api/worker/frontend với code/env mới; route mới 401 `AUTH_REQUIRED`; Harness story complete.
- [x] Thêm CI GitHub Actions `.github/workflows/ci.yml`: API, Discord bot, web và Compose base/team;
  intake #18 lane tiny. Chưa commit/push.

## Done — Local 2026-11-03

- [x] Commit triển khai `2f04131` đã push; GitHub security CI run41611694633 đạt.
- [x] API/worker non-root, read-only, caps/PID bounds; volume cũ/restore/OCR/LaTeX/migration đã kiểm.
- [x] CLI sandbox: tắt native Codex execution/subagent, agy scoped keyring broker, negative canary đạt.
- [x] Bridge cài ngoài repo 0500, systemd active; Codex/agy completion thật đạt.
- [x] Tự tạo owner theo yêu cầu; credential 0600 ngoài repo; bật local auth, kiểm 401/CSRF403/owner200.
- [x] Bật nghiên cứu bounded; một q2 thật completed, report draft; không auto-publish/apply.
- [x] Chat và link thật với Codex đạt, link needs_review.
- [x] Backup timer 02:30 + Linger, retention 14, manifest hash; restore 46 bảng và mọi tệp khớp.
- [x] Git hooks/gitleaks; API pypdf 6.21.4, production dependency audit 0.
- [x] Chat mobile Lighthouse median 91/A11y 98, JS 189→146kB, history 8→24 và timezone hydration đạt.
- [x] Research verifier shared context/batch 40/cache 24h giữ validation; benchmark 40 verdict đúng.
- [x] Kiểm tra trạng thái provider, khôi phục Ollama bridge, đồng bộ handoff/task board có archive.

## Operational Notes

API host 8000 thuộc project khác. Dùng 18000/13000. Đĩa root còn 9,74 GB khả dụng sau intake 33.
Không build sạch TeX hay bật team trước khi đủ đĩa. Không prune tài nguyên không thuộc task; giữ ảnh rollback
`*:pre-hardening-20261103`. Đừng lặp các bước owner/auth/backup đã xong. Session ngày 03/11 và
validation có lệnh/test; không dùng advisory/provider lịch sử làm hiện trạng.
