# Current Handoff

Cập nhật 2026-11-03. Đây là tóm tắt hiện hành; lịch sử đầy đủ trước khi thu gọn được giữ nguyên tại
[archive](ARCHIVE/2026-11-03-before-local-readiness-HANDOFF.md). Không coi provider/advisory cũ
trong archive là cấu hình hiện tại. Task board: [TASKS.md](TASKS.md).

## Current Goal

Hoàn tất các việc kỹ thuật local trong Now theo yêu cầu “làm hết các việc tiếp theo”, tự tạo owner;
user xác nhận chưa có tên miền. Intake #16 / `US-REMAINING-LOCAL-READINESS`, decision 0054/DEC-067.
Container hardening intake #15 đã hoàn tất. E2E và mechanical Harness proof đã đạt; story local readiness implemented. Đang lưu commit/push.

## Current Runtime

- UI: http://localhost:13000; API: http://localhost:18000/api/v1. Cổng chỉ bind 127.0.0.1.
- `AUTH_MODE=local`, `RESEARCH_AGENT_ENABLED=true`; owner đã tạo, anonymous dữ liệu401,
  mutation thiếu CSRF403. Credential chỉ trong `~/.config/business-ai-agents/owner-login.json`
  mode 0600 ngoài repo; không chép nội dung vào log/chat. User lấy tệp rồi đổi mật khẩu ở `/account`.
- AI tác vụ/chat mặc định Codex `gpt-6-luna`, effort low; embedding vẫn Mistral. Không tự đổi provider.
- API/worker UID/GID 10001, root/source read-only, cap-drop/no-new-privileges, PID 256; init storage
  root một lần chỉ CHOWN/DAC_OVERRIDE, không mạng/secret, không theo symlink. Volume cũ giữ dữ liệu.
- Bridge chạy bản cài 0500 tại `~/.local/lib/business-ai-agents/ai-cli-bridge/`, không chạy source repo.
  Codex tắt native shell/exec/subagent; agy chỉ có broker credential riêng, chặn phần còn lại của keyring.
  Khi đổi source bridge/helper phải chạy lại `scripts/install_ai_cli_bridge.sh` và canary.
- DB/SearXNG/worker/frontend + Ollama bridge hoạt động; quick tunnel và nginx basic-auth gate vẫn bật,
  nay có thêm app auth. Không in URL/token/password tunnel. Không đụng container project khác.
- Backup timer 02:30 giờ máy, persistent và Linger=yes. Đã chạy thử và restore tách biệt thành công.
  Backup `~/business-ai-agents-backups/scheduled/`, giữ 14 bản hoàn tất. Secret/env sao lưu riêng.
  Khi đổi script chạy lại `scripts/install_backup_timer.sh`.

## Completed This Session

- Keyring broker/canary + cài bridge ngoài repo; owner/auth/research; git hooks; backup timer/restore.
- Chat SSR theo phiên/no-store, lazy Markdown/API settings, server-rendered Markdown, hydration8 tin,
  mở lịch sử cũ on-demand. Dùng UTC lần render đầu rồi timezone browser để không hydration mismatch.
- Verifier shared evidence lossless, batch 40, verdict cache 24h theo nguồn/quote/offset/provider/model/
  user plan. Verdict thiếu/xung đột không được coi là đạt. Không bỏ verifier hay auto-publish.
- pypdf6.21.4 khóa và triển khai; dependency-refresh target tái dùng lớp TeX/OCR đã kiểm chứng.
- Có chat Codex thật và link công khai completed/needs_review; nghiên cứu q2 completed, report draft.
- Thu gọn handoff/task board, giữ archive và toàn bộ session lịch sử. Chưa ký nghiệm thu sản phẩm.

## Verification

- API 603 test đạt; web 205 test, typecheck/lint/build đạt. E2E81 auth-disabled +9 auth riêng đạt; xem validation.
- Container canary + live API/worker: non-root/read-only/caps/storage/restore/OCR/LaTeX/migration đạt.
- Codex canary không đọc được credential giả, không event native shell/file/MCP/subagent. Scoped
  keyring negative tests đạt. Codex/agy completion thật đạt; installed bytes/modes khớp source.
- Backup restore46 bảng và mọi hash tệp khớp trong PostgreSQL/volume riêng; fixture đã gỡ.
- Lighthouse authenticated mobile80→91/91/92 (median91), A11y 98; `/chat` first-load JS189→146kB.
- Verifier40 claim tổng hợp:26466→11995 token (−54,7%),40/40 verdict đúng. Replay8 run giảm0,88%
  payload chars. Đây không phải bằng chứng giảm20% token toàn pipeline; optimization story vẫn mở.
- Một research q2 thật:97,7s/8 call/107598 token,18 câu có citation,9 nguồn/8 domain; entity recall0,4.
- API/Discord pip-audit0; npm production0, dev/lint14 Moderate,0 High/Critical; không force downgrade.
- Gitleaks lịch sử47 commit sạch trước commit mới; pre-commit sẽ quét staged. Evidence:
  [local readiness](../docs/evaluations/local-readiness/README.md), [validation](../docs/stories/remaining-local-readiness/validation.md).

## Remaining / External Inputs

- OpenAI preflight `CHAT_API_KEY_INVALID`; Gemini key thiếu. Claude logged-in nhưng probe CLI_FAILED
  có chỉ dấu billing; không tự đổi billing/tài khoản. Ollama host+bridge tags200 nhưng0 model.
- ChatGPT per-user code có test; real OAuth consent/client ID web và tên miền chưa có. Không đánh dấu
  tích hợp thật đã nghiệm thu. Team config/runbook sẵn, chưa chuyển runtime sang team.
- Root đĩa khoảng1,1GB, home11GB lúc kiểm tra cuối; không build sạch TeX hay bật team trước khi đủ đĩa.
  Không prune/delete tài nguyên project khác hoặc ảnh rollback. Offsite backup cần đích thực.
- KPI token toàn pipeline8 câu chưa đạt/chưa được chứng minh; giữ `US-OPTIMIZATION-PROGRAM` mở.
- Chỉ Linh quyết định product acceptance Graph v2/UI và apply các draft change set. Xem TASKS.
- Tùy chọn Later (ontology/Redis/collector mới/Discord live/MinIO production) chưa được chọn triển khai.
- Pytest có warning TestClient/httpx; Vitest cảnh báo cấu hình loader của phiên bản tương lai; test đạt.

## Next Best Action

Commit/push nhánh hiện tại sau gitleaks; các kiểm tra kỹ thuật và Harness đã đạt.
Sau đó user đăng nhập tại UI bằng tệp riêng, đổi mật khẩu và xem báo cáo/draft trước khi duyệt.
Agent sau chỉ tiếp tục provider/team/offsite khi có đầu vào; không tạo lại owner hoặc cài lại dịch vụ
đã đạt nếu không có thay đổi. Giữ backup và ảnh `*:pre-hardening-20261103` làm rollback.

## Locked Direction

Local-first; PostgreSQL source of truth; graph/search là projection; `/api/v1`; deployable code dưới
`apps/`; RSS MVP; AI không tự ghi đè human fields; báo cáo và graph proposals cần human review.
Kế hoạch: `Docs/Research System Implementation Plan.md`. Không tự migration/retire local objects
sang MinIO production, không tự ký product acceptance, không ghi secret/PII vào AI_LOGS.
