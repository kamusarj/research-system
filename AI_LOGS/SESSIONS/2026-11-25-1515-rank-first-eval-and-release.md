# Cân bằng `stage_searching`, đo lại đối chứng 8 câu và rà soát phát hành

## Yêu cầu

Linh chọn thực hiện cả 2 hướng (2026-11-25, Asia/Bangkok, Antigravity, Harness intake #39, lane `normal`, story `US-OPTIMIZATION-PROGRAM`):
1. Sửa `stage_searching` sang duyệt hit theo hạng trước (`rank-first round-robin`) + tăng độ phủ trích xuất (`MAX_EXTRACT_SOURCES_PER_BATCH = 4`, `EXTRACT_PASSAGE_MAX_CHARS = 5200`, hướng dẫn giữ tên thực thể/tổ chức trong `EXTRACT_TASK`) và chạy lại bộ đối chứng 8 câu × 2 biến thể.
2. Rà soát và commit/push gói thay đổi đã kiểm chứng (kèm `.github/workflows/ci.yml`).

## Checkpoint 1 — Trước triển khai (15:15)

- Phân tích số liệu 8 câu ngày 2026-11-25 (`docs/evaluations/research-agent/2026-11-25-*`):
  - `stage_searching` duyệt hết 8 hit của truy vấn đầu (`market`) trước, khiến các góc nhìn sau (`competitors`, `use_case`) bị lấy mất URL tốt vào `seen_urls` → 3 câu `reference` và 1 câu `optimized` thiếu 1/5 góc nhìn.
  - `MAX_EXTRACT_SOURCES_PER_BATCH = 6` kéo trung bình `claims_verified` của `optimized` xuống `22,1` so với `32,9` của `reference` (`q1`: 14 vs 21; `q2`: 22 vs 31; `q8`: 15 vs 35), gây hụt 1 thực thể ở `q1`/`q2` và thiếu `competitors` ở `q8`.
- Thiết kế sửa tối thiểu:
  - `stage_searching`: lọc hit đạt `MIN_HIT_RELEVANCE` theo từng truy vấn trước, sau đó duyệt theo `hit_index` tăng dần (mọi góc nhìn nhận hit hạng 1 trước khi góc nhìn nào nhận hit hạng 2).
  - `runner.py`: đặt `EXTRACT_PASSAGE_MAX_CHARS = 5200`, `MAX_EXTRACT_SOURCES_PER_BATCH = 4` (tăng recall mỗi nguồn lên ~30+ verified claim, vẫn tiết kiệm ~35–42% token và nhanh hơn hoặc tương đương 6 nguồn/lô); cập nhật `EXTRACT_TASK` (`research-extract-v3-grounded-entities`, giống nhau ở cả hai biến thể) để giữ tên tổ chức/sản phẩm/chuẩn từ trích dẫn gốc và làm rõ phạm vi `competitors`/`use_case`.
  - Thêm test hồi quy kiểm chứng `stage_searching` không để truy vấn đầu chiếm hết nguồn của các góc nhìn sau.

## Checkpoint 2 — Sau triển khai & trước đo lại đối chứng đủ 8 câu (15:18)

- Tệp đã sửa:
  - `apps/api/app/services/research_agent/runner.py`:
    - `stage_searching`: lọc hit đạt ngưỡng liên quan trước rồi duyệt theo hạng tăng dần (`rank-first round-robin`) để mọi góc nhìn nhận các URL khớp nhất trước khi truy vấn đầu chiếm vào `seen_urls`.
    - `EXTRACT_PASSAGE_MAX_CHARS = 5200`, `MAX_EXTRACT_SOURCES_PER_BATCH = 4`, và `EXTRACT_TASK` (`research-extract-v3-grounded-entities`, giống nhau ở cả hai biến thể).
  - `apps/api/tests/test_research_agent.py`: thêm `test_stage_searching_assigns_top_hits_rank_first_across_perspectives`.
  - `docs/stories/optimization-program/design.md`: cập nhật thiết kế `rank-first round-robin` và tham số `5.200`/`4 nguồn/lô`.
- Kiểm thử:
  - Tập trung: **116 passed**, `ruff check` & `git diff --check` sạch.
  - `scripts/bin/harness-cli story verify US-OPTIMIZATION-PROGRAM`: **pass** (API **939 passed**, 4 skipped; web **236 passed** / 45 tệp).
- Bước tiếp theo: chạy lại đối chứng đủ 8 câu × 2 biến thể (`reference` rồi `optimized`) trên PostgreSQL tách biệt (`stop_on_provider_error=True`, corpus `research-corpus-20261119.json`), lưu kết quả tại `~/.cache/business-ai-agents/audit-runtime/20261125-full-eval-r2/`.

## Checkpoint 3 — Sau đo lại đối chứng 8 câu (`r2`) & trước commit/push (15:54)

- Kết quả đo lại đủ **8 câu × 2 biến thể** (`r2`, Codex `gpt-6-luna`, `source_sha256=ebe68beb70b129c0`, corpus cố định `014428db...`, PostgreSQL thử đã xóa sạch):
  - **16/16 lượt hoàn tất, 0 lỗi, 0 thiếu usage**.
  - **Độ phủ góc nhìn đạt 1,000 (5/5) ở TẤT CẢ 16/16 lượt** (8/8 `reference` và 8/8 `optimized`) — lỗi thiếu góc nhìn do `stage_searching` đã được giải quyết triệt để.
  - **Độ phủ trích dẫn**: `1,000` ở tất cả 16/16 lượt.
  - **Tổng token**: `897.992 → 481.846` (**−46,3%**, từng câu giảm từ −35,7% đến −58,2%); ký tự prompt `1.395.083 → 757.697` (−45,7%); lệnh gọi AI `71 → 48` (−32,4%); thời gian TB `142,2s → 113,5s` (−20,2%).
  - **Độ phủ thực thể trung bình**: tăng từ `0,400 → 0,450` (+12,5%): `optimized` thắng ở `q1` (`0,2→0,6`), `q5` (`0,4→0,6`), `q7` (`0,2→0,4`), hòa ở `q2/q3/q4`, chỉ thấp hơn 1 thực thể ở `q6` và `q8` (`0,6→0,4`).
  - `research-eval-compare` giảm từ 6 mục xuống còn đúng **2 mục từng câu** (`q6-roi` và `q8-sme-vietnam: độ phủ thực thể giảm`). Giữ nguyên chuẩn không hạ cổng; `US-OPTIMIZATION-PROGRAM` giữ `in_progress`.
- Lưu 3 artifact chỉ số/hash tại `docs/evaluations/research-agent/2026-11-25-r2-{reference.json,optimized.json,comparison.md}`.
- Kiểm chứng chuẩn bị phát hành:
  - `scripts/verify_second_audit_remediation.sh`: đạt (API 939 passed / 4 skipped, bot 56 passed, web 236 passed, lint/lock/shell/diff).
  - Web `eslint` + `tsc --noEmit`: sạch.
  - Cả 3 cấu hình Compose của CI (`base`, `multi-user`, `team` với `--profile local-ai`): hợp lệ.
  - `gitleaks git`: 0 leak; `gitleaks dir` chỉ cảnh báo trong `.env` và `apps/web/.next/` (đều gitignore).
  - Kiểm tra 0 job chạy nền, restart `worker`/`api`: API health 200, ẩn danh `/api/v1/graph` 401, Web `:13000/graph` 200.
- Bước tiếp theo: kiểm tra staged diff + `gitleaks protect --staged`, đóng gói commit có cấu trúc rõ ràng trên `feature/research-system-mvp`, push lên `origin` và theo dõi GitHub Actions CI.

## Checkpoint 4 — Commit & push gói thay đổi đã kiểm chứng (15:56)

- Các commit đã tạo trên nhánh `feature/research-system-mvp` (mọi commit đều qua hook `gitleaks protect --staged`, 0 leak):
  1. `14ed9fa` — `ci(ops): add GitHub Actions workflow, guarded backup/restore, and lockfile sync` (16 tệp).
  2. `d4566f6` — `fix(api): complete audit remediations, lease fencing, and research agent extraction optimization` (40 tệp).
  3. `7e24ba7` — `feat(web): redesign graph canvases in Weave style with drag/pin and interaction fixes` (30 tệp).
  4. Commit tài liệu/chứng cứ/AI_LOGS theo sau cùng (kèm phiên log này) trước khi `git push origin feature/research-system-mvp`.
- Kiểm chứng tổng thể:
  - API: **939 passed**, 4 skipped (`ruff`, `uv.lock`, migration PostgreSQL khứ hồi + 21 test PG trước đó).
  - Discord bot: **56 passed**, `ruff` sạch.
  - Web: **236 passed** / 45 tệp, `eslint`, `tsc --noEmit`, `npm run build` sạch.
  - Compose: cả 3 cấu hình `base`, `multi-user`, `team` (`--profile local-ai`) hợp lệ.
  - Runtime local: `worker`/`api` đã restart, API health `200`, ẩn danh `/api/v1/graph` `401`, Web `:13000/graph` `200`.
- Còn mở:
  - `US-OPTIMIZATION-PROGRAM`: giữ `in_progress` do 2 điểm dao động 1 thực thể từng câu (`q6-roi`, `q8-sme-vietnam`) trong khi 16/16 lượt đạt 5/5 góc nhìn, 100% trích dẫn, −46,3% token và `entity_recall` TB tăng `0,400 → 0,450`.
  - Theo dõi kết quả GitHub Actions run trên `origin/feature/research-system-mvp` sau khi push; Linh nghiệm thu UI Weave/Graph v2 trên `:13000`.

## Checkpoint 5 — Xác minh GitHub Actions CI & Security xanh toàn bộ (16:00)

- Lượt đẩy đầu tiên (`175890f`, run `45580700185`) đạt 4/5 job `ci` + `security` (`45580700169`), riêng job `API (ruff, pytest)` báo `ModuleNotFoundError: No module named 'tests'` vì `.github/workflows/ci.yml` gọi `uv run pytest` thay vì `uv run --frozen python -m pytest`.
- Intake #40 (tiny): sửa `.github/workflows/ci.yml` sang `uv run --frozen ruff check .` và `uv run --frozen python -m pytest`, commit `bf5c69d` và push.
- Kết quả GitHub Actions thực tế trên `bf5c69d`:
  - **`ci` run `45581065933`: SUCCESS** — đạt cả 5/5 job (`API`, `Discord bot`, `Web`, `PostgreSQL migration and model parity`, `Compose config`).
  - **`security` run `45581066073`: SUCCESS**.
