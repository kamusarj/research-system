# Session Log

## Context

- User request: thực hiện các đề xuất audit và thử Mistral; nhánh công việc này phụ trách release/ops.
- Agent: Codex `/root/fix_release`, dưới intake #19 / `US-AUDIT-REMEDIATION`, decision 0056.
- Date/time: 2026-11-19 09:01 +07.

## Work Done

- Files changed: `scripts/team.sh`, `scripts/backup_local.py`,
  `scripts/verify_postgres_migrations.sh`, `apps/api/tests/test_backup_retention.py`,
  `apps/api/tests/test_frontend_dependency_sync.py`, `apps/web/scripts/ensure-dependencies.sh`,
  `apps/web/package.json`, `apps/web/package-lock.json`, `docker-compose.yml`,
  `docker-compose.multi-user.yml`, `.github/workflows/ci.yml`.
- Team backup dùng cùng engine với timer, luôn quiesce, resume đúng dịch vụ đang chạy,
  giữ manifest/checksum/retention có nhận dạng. Explicit `TEAM_ENV_FILE` giữ đúng Compose project.
- Lock theo repo trong cache người dùng ngăn timer và backup thủ công ở các destination khác nhau
  mở hai khoảng quiesce/resume chồng lấn. Không xóa backup cũ thiếu manifest của engine.
- Frontend kiểm hash package/lockfile và Node ABI/platform/architecture, cùng toàn bộ cây dependency;
  lỗi cài đặt không cập nhật marker. Cả base và multi-user chạy bước này trước serve/build.
- Next + eslint-config-next 15.5.29; cập nhật tương thích TS-ESLint 8.73.0/minimatch 11.0.9;
  không force hoặc nâng major framework.
- CI giữ workflow có sẵn, thêm uv lock check, Node 22 khớp Docker và job PostgreSQL riêng.
  Script migration bắt buộc URL PostgreSQL rõ ràng, DB rỗng tên `baa_ci_*`; không suy URL từ .env.

## Reasoning / Decisions

- Tái sử dụng backup engine thay vì duy trì hai chính sách consistency/retention.
- Dùng lockfile hash vì top-level semver vẫn có thể hợp lệ sau một bản vá chỉ đổi lockfile.
- Giữ Next 15 maintenance, đối chiếu release bảo mật chính thức:
  https://github.com/vercel/next.js/releases/tag/v15.5.29
- Dev advisory đối chiếu https://github.com/advisories/GHSA-g3hv-75wg-m249

## Verification

- `uv run --offline --no-sync pytest -q tests/test_backup_retention.py tests/test_frontend_dependency_sync.py`:
  6/6 passed, bao gồm delete race, failed dump resume, cross-destination lock, lock-only update và install failure.
- Ruff targeted tests + `scripts/backup_local.py`: passed.
- Web `npm test`: 44 files / 226 tests passed; `npm run lint`, `npm run typecheck`: passed.
- `npm install --package-lock-only ...`, `npm audit fix --package-lock-only`, `npm install --include=dev`:
  áp dụng dependency patch; full + production `npm audit` đều 0 advisory.
- `npm ls --include=dev --all`: passed. Workflow YAML parsed với js-yaml.
- `bash -n`/`sh -n` cho các entrypoint; base + multi-user Compose `config -q`: passed.
- `git diff --check`: passed tại thời điểm kiểm tra.

## Known Issues

- Node/Vite config cảnh báo định dạng CommonJS/ESM, không chặn test.
- Không build ảnh hoặc restart runtime ở nhánh này do đĩa root hạn chế.
- PostgreSQL smoke script/job đã tạo; root thực thi trên DB tách biệt và ghi kết quả riêng.
- GitHub Actions chưa chạy trên remote; không commit/push trong nhánh công việc này.
- Root phụ trách Mistral, deploy runtime, AI_LOGS/HANDOFF/TASKS và tổng hợp evidence.

## Next Best Action

Root chạy PostgreSQL smoke trên DB tách biệt; reinstall backup timer để bản engine cài ngoài repo
nhận shared lock, rồi cập nhật frontend runtime khi đủ dung lượng và hoàn tất kiểm thử tổng hợp.

## Follow-up: Custom Team Project and Independent DNS Recheck

- Theo review tiếp của root, auto-detect `.env.team` của timer vẫn thêm `-p businessaiagents`,
  nên có thể chọn sai stack nếu operator đổi `COMPOSE_PROJECT_NAME`. Đã bỏ override này cho cả
  team env tự phát hiện và explicit; chỉ local fallback giữ project mặc định.
- Regression cùng luồng backup/delete/quiesce chạy ở hai chế độ explicit và auto-detect team env;
  local fallback cũng kiểm tra project cố định. Suite ops nay 7 test.
- Không đổi app Python hoặc runtime trong lúc benchmark của root đang chạy.
- Recheck độc lập DNSfix của agent local với cùng resolver tổng hợp chậm 0,65 giây:
  request budget 0,1 giây nay trả `CHAT_PROVIDER_TIMEOUT` sau 0,102 giây (trước 0,700 giây).
  Không gọi model thật hay dùng credential thật trong phép kiểm tra này.
- Root cần reinstall timer thêm một lần sau bản sửa custom project này; không khởi chạy backup
  trong lúc benchmark còn chạy.
