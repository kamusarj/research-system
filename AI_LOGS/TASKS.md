# Task Board

Cập nhật 2026-11-03; trạng thái hiện hành ở [HANDOFF](HANDOFF.md). Bảng cũ gồm toàn bộ Done lịch sử
được giữ nguyên tại [archive](ARCHIVE/2026-11-03-before-local-readiness-TASKS.md).

## Now

- [ ] Commit/push thay đổi local readiness; E2E và proof/trace đã đạt.
- [ ] KPI tối ưu token: cần so sánh lại8 câu naive/optimized trên cùng provider/config; verifier đã
  giảm54,7% ở benchmark riêng, chưa đủ kết luận20% toàn pipeline. Không hạ chuẩn bằng chứng.
- [ ] Linh đăng nhập http://localhost:13000 bằng tệp riêng trên máy, đổi mật khẩu tại `/account`,
  kiểm tra chat/báo cáo và hàng chờ link mới. Không gửi mật khẩu vào chat hay AI_LOGS.

## Blocked / Needs Owner Inputs

- [ ] Gemini: cung cấp key qua `.env`/secret; sau đó mới chọn embedding Gemini và re-index theo0050.
- [ ] OpenAI: thay key không hợp lệ nếu muốn dùng; chạy `verify-openai` trước khi chuyển mặc định.
- [ ] Claude: kiểm tra tài khoản/billing do native probe đang lỗi; Codex và agy hiện dùng được.
- [ ] Ollama: chọn/tải model phù hợp tài nguyên nếu muốn dùng; service/bridge đã nối, hiện0 model.
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

## Done — Local 2026-11-03

- [x] API/worker non-root, read-only, caps/PID bounds; volume cũ/restore/OCR/LaTeX/migration đã kiểm.
- [x] CLI sandbox: tắt native Codex execution/subagent, agy scoped keyring broker, negative canary đạt.
- [x] Bridge cài ngoài repo0500, systemd active; Codex/agy completion thật đạt.
- [x] Tự tạo owner theo yêu cầu; credential0600 ngoài repo; bật local auth, kiểm401/CSRF403/owner200.
- [x] Bật nghiên cứu bounded; một q2 thật completed, report draft; không auto-publish/apply.
- [x] Chat và link thật với Codex đạt, link needs_review.
- [x] Backup timer 02:30 + Linger, retention 14, manifest hash; restore46 bảng và mọi tệp khớp.
- [x] Git hooks/gitleaks; API pypdf6.21.4, production dependency audit0.
- [x] Chat mobile Lighthouse median91/A11y 98, JS189→146kB, history8→24 và timezone hydration đạt.
- [x] Research verifier shared context/batch 40/cache 24h giữ validation; benchmark40 verdict đúng.
- [x] Kiểm tra trạng thái provider, khôi phục Ollama bridge, đồng bộ handoff/task board có archive.

## Operational Notes

API host8000 thuộc project khác; dùng18000/13000. Root đĩa khoảng1,1GB, home11GB lúc kiểm tra.
Không prune tài nguyên không thuộc task. Đừng lặp các bước owner/auth/backup đã xong.
Session ngày03/11 và validation có lệnh/test; không dùng advisory/provider lịch sử làm hiện trạng.
