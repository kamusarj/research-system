# Session — Hoàn thiện local readiness

Date: 2026-11-03, Asia/Bangkok. Agent: Codex. Intake #16, high-risk,
`US-REMAINING-LOCAL-READINESS`, decision 0054/DEC-067. Giữ nguyên toàn bộ thay đổi container
phiên trước (intake #15, session1138); không chạm dữ liệu/tài nguyên project khác.

## User request

Đọc LOG AI, tiếp tục công việc và “làm hết các việc tiếp theo”. User cho phép tự tạo tài khoản
owner và trả lời chưa có tên miền. Thực hiện các mục kỹ thuật Now có thể hoàn tất trên máy;
không đăng ký credential, OAuth consent hoặc ký nghiệm thu sản phẩm thay người sở hữu.

## Files changed

- `apps/api/app/ai_cli_bridge.py`, `ai_cli_keyring_proxy.py`, tests bridge/policy;
  installer, systemd bridge unit, `scripts/verify_cli_isolation.py`.
- `scripts/backup_local.py`, installer/timer/service và `test_backup_retention.py`.
- Research `services/research_agent/{evidence,runner}.py`, tests cache/compaction/verdict.
- Chat server route/client workspace, bootstrap/window/URL helpers, Markdown/media/client wrapper,
  fonts/layout/CSS, unit tests và E2E auth/history.
- API Dockerfile/install_dependencies/pyproject/uv.lock (pypdf6.21.4), optional Ollama bridge compose.
- README, team runbook, implementation plan delta, decision0049 amendment/0054, story packet,
  optimization validation follow-up và sanitized evaluation artifacts.
- `scripts/verify_local_readiness.sh`; AI_LOGS HANDOFF/TASKS/DECISIONS và bản archive nguyên vẹn.
- Phiên container trước còn chung working tree: storage init, LaTeX limits/tests, hardening verifier,
  compose local/team và decision 0053/story/session của phiên đó được giữ và sẽ commit cùng đợt này.

## Decisions made

- Giữ Codex mặc định, embedding Mistral; không tự đổi sang key đang lỗi hoặc tải Ollama model.
- Tắt native shell/unified_exec/subagent Codex. Agy chỉ có broker Secret Service đúng credential
  ứng dụng, không toàn keyring; session/path/attributes/write đều kiểm tra. Cho refresh đúng scope.
- Bridge bản cài 0500 ngoài repo, Python hệ thống `dbus`/`gi`, daemon riêng và dọn process group.
  Tối đa2 CLI song song nhưng tuần tự từng backend để không tranh refresh.
- Owner password ngẫu nhiên qua stdin; tệp private0600 ngoài repo, không log nội dung. Bật local
  auth/research theo phạm vi user đã giao. Chưa bật team vì chưa có domain/HTTPS và thiếu đĩa.
- Timer 02:30 + Linger, backup quiesce API/worker, verify dump/tar/hash, retention 14 chỉ backup có
  manifest của script. Resume đúng dịch vụ đã chạy cả khi lỗi. Offsite chưa chọn đích.
- Chat SSR có session/no-store và user binding; window 8 chỉ giới hạn hydration/render, toàn bộ
  lịch sử vẫn lấy được. UTC lần render đầu, địa phương sau hydration để không lỗi React418.
- Verifier giữ mọi quote/window, batch 40, cache verdict 24h theo full source hash/offset/model/user
  plan; thiếu/unknown/xung đột verdict thì không dùng claim. Không bỏ verifier hoặc auto-publish.
- Không dùng benchmark verifier riêng để ký KPI giảm20% toàn pipeline. Story optimization vẫn mở.
- Không force npm downgrade; không xóa cache/image/volume project khác để lấy đĩa.

## Commands/tests run

- Startup đọc HANDOFF→TASKS→DECISIONS→docs liên quan; bootstrap Harness; intake/high-risk packet,
  active matrix; OpenAI docs skill và official docs cho khả năng tắt native Codex shell.
- `scripts/install_ai_cli_bridge.sh`, real Codex/agy probe; unit bridge/policy 38 đạt.
- `python3 scripts/verify_cli_isolation.py --codex-canary`: installed bytes/modes/service path,
  keyring scoped read + foreign/mixed/unknown-session/write denied; fake credential không đọc được,
  không event command_execution/file_change/MCP/subagent. Không in secret/keyring value.
- Tạo owner bằng `app.operations create-user --password-stdin`, lưu file private ngoài repo;
  API/worker local multi-user recreate healthy, auth login/data200, anonymous401, CSRF thiếu403.
- `scripts/install-git-hooks.sh`; gitleaks toàn lịch sử47 commit0 secret trước commit mới.
- `scripts/install_backup_timer.sh`; start backup service success; `loginctl enable-linger` success.
  Diễn tập pg_restore trong PostgreSQL tmpfs và tar restore UID10001 vào volume tạm:46 bảng,
  owner tồn tại, mọi SHA-256 tệp khớp. Fixture gỡ sau kiểm tra.
- `uv lock --upgrade-package pypdf`, khóa>=6.21.4; dependency refresh trên base root đã kiểm chứng,
  runtime API/worker build/recreate. Lock hash source/image trùng; `pip check` sạch.
- pip-audit API runtime53 dependency0 và Discord lockfile0. npm production audit0; full audit14
  Moderate dev/lint,0 High/Critical. Không dùng `npm audit fix --force`.
- `bash scripts/verify_container_hardening.sh --live` trên ảnh mới đạt: isolated migration/check,
  non-root/caps/read-only, legacy storage/symlink/restore, OCR, LaTeX với thread competition.
- Full API 603 test đạt; research targeted 35; web 205 test/typecheck/lint/production build đạt.
  Mechanical proof cuối bằng `bash scripts/verify_local_readiness.sh` đã đạt.
- Browser isolated project `baa-readiness-e2e`: PG tmpfs/volume riêng, API28000, Next 23000;
  không dùng credentials thật, không native CLI/OAuth. Auth 9/9 đạt gồm owner/viewer + SSR history
  24 tin/múi giờ Pacific/Honolulu. History fixture repeat 9/9 đạt; full 81/81 case cuối đạt,9 auth skip ở mode disabled được chạy riêng 9/9.
- Live owner browser ở production3 viewport: không pageerror/tràn ngang; private/no-store,
  anonymous không nhận selected session, cookie không serialize. Full history có unit/E2E riêng.
- Lighthouse mobile production cùng hội thoại, `/auth/me`200: baseline80/A11y 98; cuối91/91/92,
  A11y 98, LCP khoảng3,3s, TBT36/37/33ms. First-load JS189→146kB. Chỉ lưu số đo JSON.
- Native verifier benchmark40 claim:2 call/26466 token→1 call/11995 token,−54,7%,40/40 verdict đúng
  ở cả hai. Replay8 run giảm0,88% payload chars (không phải token provider).
- Research q2 thật completed97,7s,8 call/107598 token,18 câu có citation/9 nguồn/8 domain,
  23 claim verified, entity recall0,4, report draft. Không suy rộng chất lượng/chi phí từ một câu.
- Chat Codex thật trả lời, không tạo change set; link Anthropic public completed/needs_review,
  không auto-approve. Evidence sanitized ở `docs/evaluations/local-readiness/`.
- Provider: OpenAI preflight key invalid; Claude logged-in nhưng CLI_FAILED với chỉ dấu billing;
  Ollama host/bridge tags200, inventory0 model; Gemini key thiếu. Không in credential/error body.
- `git fetch origin`: ahead46/behind0 trước commit; GitHub repo public, user có quyền admin.
  `git diff --check`, bash syntax và Markdown fences đạt trước bước đóng phiên.

## Verification result

Đợt triển khai local đã đạt kiểm tra cuối: API603, web205, E2E81+auth9, production build,
platform canary và fresh Harness completion. Trace15 detailed3/3 và context3/3. Commit triển khai
`2f04131` đã push, GitHub security CI đạt; chi tiết đóng phiên ở dưới.
Không đánh dấu provider/team/owner acceptance hoặc KPI toàn pipeline đã xong.

## Known issues

- Hai vòng E2E đầu có timeout khác nhau: document editor 30s (rerun 3/3 đạt), history assertion5s
  trước response (repeat 9/9 đạt). Test history hiện đợi response trước assert; không đổi app
  hoặc tăng timeout toàn bộ suite. Vòng cuối81/81 đã đạt.
- Live smoke đầu bắt React418 do server UTC/browser local; đã sửa, browser3 viewport và E2E
  timezone3/3 đạt. Đây là lỗi đã giải quyết, không được mang sang Known Issues hiện hành.
- Docker `cp` không lấy được tệp trong tmpfs dù `exec` thấy; dùng `docker exec cat` để lấy metric.
  Có lỗi fixture ban đầu (YAML tmpfs chưa quote dấu phẩy, provider default Mistral không hợp lệ
  cho graph chat) và poll sai GET link detail; đã sửa script test, không thay API contract.
- OpenAI/Gemini/Claude/Ollama và ChatGPT/domain/offsite cần đầu vào như HANDOFF; không tự giả lập.
- Root còn khoảng1,1GB, home11GB. Không clean build TeX/team trên đĩa hiện tại; giữ ảnh rollback.
- Toàn pipeline vẫn chưa chứng minh giảm20% token8 câu. npm dev14 Moderate còn lại.
- TestClient/httpx deprecation và Vitest future-loader warning không làm test fail.

## Next best action

User lấy credential từ tệp riêng trên máy, đổi mật khẩu và tự duyệt draft/Graph/UI.
Story local readiness đã implemented; mã đã commit/push và CI đạt.
Agent sau dùng HANDOFF/TASKS ngắn mới, chỉ mở archive khi cần lịch sử; không tạo lại owner hoặc
cài lại dịch vụ đã kiểm chứng nếu source/config không đổi.

## Final verification / Handoff reconciliation

- Full E2E cuối81/81 đạt (9 auth skip có chủ ý); enabled-auth9/9 đạt riêng, tổng90 case.
- Fresh `story complete US-REMAINING-LOCAL-READINESS` pass toàn mechanical proof gồm production
  build; story implemented với unit/integration/e2e/platform=yes. Không đóng optimization KPI.
- Backlog1 đã đóng: handoff/task board hiện hành ngắn, archive giữ nguyên nội dung cũ và có liên kết;
  không tuyên bố thời gian tiếp quản đã đo khi chưa instrument.
- ChatGPT story planned cũ được sửa in_progress, unit/integration=yes theo code/tests; real OAuth
  và web client/domain vẫn chưa xác nhận, không đánh dấu implemented.
- Backup chạy lại sau smoke success; installed bridge/helper/backup bytes đều khớp source.
  API/worker healthy sau resume. Ollama bridge đã recreate dùng ảnh vá mới, tags được kiểm lại.
- Fixture E2E/volume/network riêng và Next dev đã gỡ; raw private Lighthouse/error/fixture credentials
  đã xóa khỏi tmp. Giữ owner file0600 ngoài repo, backup và ảnh pre-hardening làm rollback.
- Chuẩn bị commit/push sau gitleaks; kết quả Git/CI sẽ bổ sung bên dưới trước khi kết thúc.

## Pre-commit review

Hook chặn3 generic-api-key match:2 lần public Docker image tag trong session cũ và password
fixture của lệnh Compose config-only. Không có secret thật. Thêm đúng public image literal vào
allowlist hiện có; đổi password fixture thành giá trị test ngắn. Không bỏ qua hook hoặc tắt luật.
Rerun container script và staged gitleaks trước commit. Trace13 detailed đạt nhưng thiếu tên command
trong files_read; trace14 ghi lại command nên context3/3, nhưng scorer đòi chữ unavailable cho
metadata không được đo. Trace closeout kế tiếp ghi đúng cả context và giải thích metadata.

## Git / CI closeout

- Implementation commit: `2f04131fa10586f366e78ce0f65b93728b80df6f`,
  `feat(local): harden runtime and complete local readiness`. Pre-commit gitleaks sạch.
- Push fast-forward lên `origin/feature/research-system-mvp` thành công, không force; trước đợt
  này46 commit local chờ, sau push branch ahead0/behind0. Không merge vào nhánh mặc định.
- [GitHub security CI](https://github.com/kamusarj/research-system/actions/runs/41611694633)
  success: secrets toàn lịch sử và production dependencies npm/API/Discord đều đạt.
- Platform script sau fixture change đạt lại; auth local bật, anonymous401, health200;
  Ollama bridge ảnh vá mới tags200/0 model. Backup cuối Result=success, ExecMainStatus=0.
- Harness story implemented; trace13/15 detailed3/3, trace15 context3/3. Backlog1 đã đóng;
  backlog2 chỉ là cải thiện wording metadata scorer, không ảnh hưởng runtime và ngoài phạm vi phiên.
- Bản ghi handoff/task/session/progress cuối được lưu trong commit tài liệu tiếp theo; không có
  thay đổi code sau verification. Các đầu vào bên ngoài và KPI toàn pipeline vẫn chưa được ký xong.
