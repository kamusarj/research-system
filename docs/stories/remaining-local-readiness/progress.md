# Progress — 2026-11-03

- CLI sandbox/keyring broker đã triển khai; Codex probe 6,4s và Antigravity 51,1s đạt.
  Broker chỉ expose service=gemini/username=antigravity, chặn đọc khác/mixed; không in secret.
- Bridge đã cài mode 0500 ngoài repo, systemd active với ExecStart mới. 38 test bridge/policy đạt.
- User yêu cầu tự tạo owner, chưa có tên miền. Đã sao lưu private ngoài repo, tạo owner qua stdin;
  credential chỉ ở `~/.config/business-ai-agents/owner-login.json` mode 0600. Không ghi nội dung.
- AUTH_MODE=local và RESEARCH_AGENT_ENABLED=true; API/worker đã recreate. Anonymous dữ liệu 401;
  owner login và dữ liệu authenticated 200; cấu hình local cookie phù hợp HTTP localhost.
- Git hooks đã bật. Backup timer đã cài 02:30 giờ máy, lần chạy thử success. Restore vào PostgreSQL
  tmpfs/volume riêng đạt: 46 bảng, owner tồn tại, mọi hash tài liệu khớp; fixture đã gỡ.
- `scripts/verify_cli_isolation.py --codex-canary` đạt: không có event shell/file/MCP/subagent,
  canary giả không đọc được; keyring chặn foreign/mixed/session/write và code installed khớp source.
- Research: `compact_entailment_payload` bảo toàn mọi cửa sổ nguồn, giảm 0,9% payload trên replay
  8 run cũ (chỉ số char, không gọi provider). Thêm cache từng verdict 24h theo evidence/offset/
  model/version/user plan, không tái dùng verdict không hợp lệ; test bỏ batch cache vẫn không cần
  gọi verifier khi lặp bằng chứng. 33 test research đã đạt trước các thay đổi test bổ sung.
- Chat: route server prefetch qua session/no-store, dữ liệu bind userId, lazy API settings;
  giữ client path khi auth disabled. Baseline Lighthouse mobile 80/A11y98; bản SSR đầu 82/98.
  Vừa sửa remount anonymous→owner gây thay DOM/LCP sau hydration; đang đo bản stable.
- Host production build và type/lint đạt trước bản identity cuối. Docker frontend đã restart/build
  hai lần; runtime owner auth vẫn tốt. Full integration/browser/quality checks còn phải hoàn tất.
- Chưa commit/push thay đổi; giữ toàn bộ việc container phiên trước. Story chính vẫn in_progress.

- Native verifier benchmark 40 claim: trước 2 call/26466 token, sau 1 call/11995 token (−54,7%); 40/40 verdict đúng ở cả hai. Đây là benchmark verifier tổng hợp, không phải chi phí toàn pipeline.
- Ollama host active nhưng 0 model; đã khôi phục bridge local-ai restricted và container gọi tags 200. Không đổi AI mặc định hoặc tự tải model. OpenAI preflight CHAT_API_KEY_INVALID. Claude auth Pro còn logged-in nhưng synthetic call CLI_FAILED có chỉ dấu billing; cần điều tra/đầu vào tài khoản nếu còn lỗi.
- npm production audit 0; audit đầy đủ có 14 Moderate thuộc công cụ lint/dev, không High/Critical; không chạy force downgrade.
- Backend batch verifier hiện 40; cần rebuild/restart API/worker cuối vì module runtime cũ đã load trước thay đổi này (source bind mới đã có).
- Frontend hiện có server-rendered Markdown slots + parser lazy, window 8, font preloads Latin/Vietnamese. First-load JS /chat 189→146 kB. Lighthouse xác nhận /auth/me 200; các tab bị Lighthouse đóng sau run nên guard tab cũ báo sai đã sửa, các số baseline là authenticated. Mobile trước window 8 đạt89/98; đang đo bounded-window.
- Timer đã enable-linger thành công để hoạt động khi đăng xuất; backup restore đã được thử thực.

- pypdf 6.21.2 có 7 CVE mới; đã khóa 6.21.4, thêm refresh-dependencies để cập nhật trên lớp TeX cũ. API/worker đã build/recreate; pip-audit runtime 53 packages, 0 lỗ hổng. Full API tests đạt (603 collected), ruff đang sạch.
- Web unit 205/205, typecheck đạt. Lighthouse sau giới hạn RSC history: 91/90/91, nhưng live browser bắt hydration #418 do UTC/server và giờ browser; đang sửa deterministic UTC lần đầu, localize sau hydration. Phải đo lại sau bản này.
- E2E stack cô lập đã lên (DB tmpfs, API/worker riêng, frontend23000). Một test document brainstorm timeout30s; rerun3/3 đạt. Chưa xác định nguồn chậm; không thay logic app để che lỗi. Fixture bổ sung fake Deepseek; không phải dữ liệu production.
- Restore/container canary cuối với ảnh pypdf mới đạt; timer active, Linger=yes. Gitleaks toàn lịch sử 47 commit không có secret; origin đã fetch, nhánh ahead46/behind0.

- Bản cuối timezone hydration đã đo91/91/92, A11y98; browser thật3 viewport không pageerror, private/no-store và anonymous isolation đạt. Auth E2E9/9 gồm timezone Honolulu/history24 tin→8→16→24, fetch lịch sử một lần.
- Chat Codex và public link thật đạt: link completed/needs_review; q2 nghiên cứu thật completed97,7s/8 call/107598 token,18 câu có citation/9 nguồn, report draft.
- E2E trước có timeout history5s; lặp9/9 đạt, test nay đợi response trước assert DOM. Đang chạy lượt tổng hợp cuối.
- HANDOFF/TASKS đã thu gọn, archive giữ nguyên bản trước. Story ChatGPT planned cũ được sửa in_progress với proof unit/integration, không giả real OAuth. Chuẩn bị chốt proof/trace/commit/push.

- E2E cuối81/81 + auth9/9 đạt, fixture cleanup xong. Story complete đã rerun mechanical proof và pass; story implemented. Backlog1 đã đóng; pending commit/push/CI. Backup sau smoke success, installed source byte match.
