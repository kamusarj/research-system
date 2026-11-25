# Tối ưu trích xuất đoạn nguyên văn cho Research Agent (`US-OPTIMIZATION-PROGRAM`)

## Yêu cầu

Tiếp tục công việc bàn giao từ Codex (intake 37) cho story `US-OPTIMIZATION-PROGRAM`: xác nhận tiến độ thực tế qua `AGENTS.md`, `AI_LOGS/` (repo không có `ai-handoff/`), `git status`/`git diff`, chạy test liên quan và triển khai tối ưu + kiểm chứng KPI đối chứng. Antigravity, 2026-11-25 (Asia/Bangkok), Harness intake 38, lane `normal`.

## Checkpoint 1 — Trước triển khai (13:40)

- Xác nhận hiện trạng:
  - Nhánh `feature/research-system-mvp` (HEAD `b9a3ffa`, 76 file tracked đã sửa + untracked từ các phiên trước).
  - Kiểm thử tập trung `tests/test_research_eval.py`, `tests/test_research_agent.py`, `tests/test_research_execution_guards.py`, `tests/test_operations.py`: **112 passed**, `ruff check` sạch, `git diff --check` sạch.
  - Runtime local: API `:18000` health 200, Web `/graph` `:13000` 200, `business-ai-agents-ai-cli-bridge.service` active, `/` trống 9,1 GiB.
- Chẩn đoán nguyên nhân `optimized` chưa giảm được 20% token so với `reference` (0 LLM call, phân tích offline trên corpus cố định `research-corpus-20261119.json` gồm 158 nguồn / 8 câu hỏi):
  - Trên toàn bộ 8 câu hỏi: `near_dups = 0`, `max_per_dom <= 3` → cờ `dedup` không loại nguồn nào.
  - Đánh giá dùng cache lạnh riêng từng lượt (`salt = uuid4`) và mỗi câu có câu hỏi khác nhau → `llm_cache_hits = 0`.
  - `web_cache` và `parallel` không giảm token LLM.
  - Kết quả: cả `reference` lẫn `optimized` đều gửi toàn bộ ~12 nguồn × đến 12.000 ký tự thô (~150–176K ký tự prompt, 5–6 lệnh gọi trích xuất). Ba lượt đối chứng `q1-market-size` trước đó cho chênh lệch token chỉ `-0,3%`, `-1,0%`, `+0,1%`.
- Thiết kế sửa tối thiểu:
  - Thêm bộ chọn đoạn nguyên văn tất định `select_relevant_passages` trong `apps/api/app/services/research_agent/evidence.py`, cắt theo đúng offset `(start, end)` từ `source.content_text` (mọi đoạn chọn là chuỗi con nguyên văn 100%, gộp liền các đoạn kề nhau).
  - Gắn cờ `passage_filter` trong `VARIANTS`: `False` cho `naive` và `reference` (giữ nguyên 100% hành vi baseline), `True` cho `optimized`.
  - Giới hạn mỗi nguồn trích xuất ở `5.000` ký tự nguyên văn chọn lọc và tối đa `4` nguồn mỗi lô khi bật `passage_filter` (giảm từ 5–6 xuống ~3 lô trích xuất, giảm ~52,9% ký tự đầu vào trên corpus mô phỏng, giữ 100% thực thể mục tiêu trên cả 8 câu).
  - Giữ nguyên `source.content_text` đầy đủ để đối chiếu `match_quote` và cửa sổ kiểm chứng suy luận; không hạ bất kỳ cổng chất lượng hay thay đổi hành vi `reference`/`naive`.

## Checkpoint 2 — Sau triển khai & trước đo đối chứng thật (13:44)

- Tệp đã sửa:
  - `apps/api/app/services/research_agent/evidence.py`: thêm `select_relevant_passages` chọn đoạn nguyên văn theo đúng offset `(start, end)`, gộp đoạn liền kề an toàn trong ngân sách ký tự.
  - `apps/api/app/services/research_agent/runner.py`: thêm cờ `passage_filter` trong `VARIANTS` (`True` ở `optimized`, `False` ở `reference`/`naive`), sửa mặc định `flags` lấy theo `run.variant`, áp `EXTRACT_PASSAGE_MAX_CHARS = 5000` và `MAX_EXTRACT_SOURCES_PER_BATCH = 4` khi bật `passage_filter`, ghi thêm `extract_raw_chars`/`extract_input_chars` vào metrics.
  - `apps/api/tests/test_research_agent.py`: thêm 3 test đơn vị/tích hợp kiểm tra chuỗi con nguyên văn, tách văn bản dài không xuống dòng, giảm prompt/số lô ở `optimized` trong khi giữ `reference` đầy đủ và `match_quote` khớp toàn văn gốc.
  - `docs/stories/optimization-program/design.md`, `docs/evaluations/research-agent/README.md`: ghi nhận cờ `passage_filter`.
- Kiểm thử:
  - `pytest tests/test_research_eval.py tests/test_research_agent.py tests/test_research_execution_guards.py tests/test_operations.py`: **115 passed**.
  - `ruff check` & `git diff --check`: sạch.
- Bước tiếp theo: chạy đối chứng thật 1 câu (`q1-market-size`) trên PostgreSQL thử tách biệt với corpus cố định `research-corpus-20261119.json` và `--stop-on-provider-error` để đo chênh lệch token thực tế và xác nhận hạn mức Codex trước khi chạy bộ đầy đủ.

## Checkpoint 3 — Sau mẫu 1 câu & trước đo đối chứng đủ 8 câu (13:54)

- Kết quả mẫu 1 câu `q1-market-size` (Codex `gpt-6-luna`, corpus `research-corpus-20261119.json`, DB tách biệt đã xóa):
  - `reference`: `107.020` token, 8 call, `150.946` ký tự prompt (`extract=119.757/119.757`), 102,6 giây, 24 claim verified, 5/5 góc nhìn, 100% trích dẫn, entity recall 0,2, `usage_missing=0`.
  - `optimized` (4 nguồn/lô): `80.434` token (**−24,8%**), 6 call, `77.843` ký tự prompt (`extract=54.244/122.067`), 82,2 giây, 18 claim verified, 5/5 góc nhìn, 100% trích dẫn, entity recall 0,2, `usage_missing=0`.
  - `optimized` (6 nguồn/lô, `MAX_EXTRACT_SOURCES_PER_BATCH = 6`): **`55.587` token (−48,1%)**, 5 call (−37,5%), `83.896` ký tự prompt (`extract=54.235/119.757`), 87,5 giây, **25 claim verified**, `qvr=0,897`, 5/5 góc nhìn, 100% trích dẫn, entity recall 0,2, `usage_missing=0`.
- Tinh chỉnh trước khi đo đủ 8 câu:
  - Chốt `MAX_EXTRACT_SOURCES_PER_BATCH = 6` trong `runner.py` và `design.md`.
  - Làm rõ `WRITE_TASK` (`research-write-v3-all-perspectives`, giống nhau cho cả `reference` và `optimized`) để writer tự sinh mục riêng cho từng góc nhìn có nhận định kiểm chứng thay vì rơi vào fallback 1 câu/mục.
- Kiểm chứng trước khi đo 8 câu:
  - `ruff check` & `git diff --check`: sạch.
  - `scripts/bin/harness-cli story verify US-OPTIMIZATION-PROGRAM`: **pass** (API **938 passed**, 4 skipped; web **236 passed** / 45 tệp).
- Bước tiếp theo: chạy đối chứng đầy đủ **8 câu × 2 biến thể** (`reference` rồi `optimized`) trên PostgreSQL tách biệt, corpus cố định `research-corpus-20261119.json`, `stop_on_provider_error=True`, lưu artifact ngoài repo tại `~/.cache/business-ai-agents/audit-runtime/20261125-full-eval/` và chạy `research-eval-compare`.

## Checkpoint 4 — Sau đo đối chứng đủ 8 câu & đóng phiên (14:28)

### Tệp thay đổi (tổng hợp phiên)

- `apps/api/app/services/research_agent/evidence.py`: thêm `select_relevant_passages` (chọn đoạn nguyên văn đúng offset `(start, end)`, giữ nguyên chuỗi con, gộp đoạn liền kề trong giới hạn ký tự).
- `apps/api/app/services/research_agent/runner.py`: thêm cờ `passage_filter` trong `VARIANTS` (`True` cho `optimized`, `False` giữ nguyên baseline cho `reference`/`naive`); sửa mặc định `flags` lấy theo `run.variant`; áp `EXTRACT_PASSAGE_MAX_CHARS = 5000` và `MAX_EXTRACT_SOURCES_PER_BATCH = 6`; làm rõ `WRITE_TASK` (`research-write-v3-all-perspectives`) cho cả hai biến thể; thêm metric `extract_raw_chars`/`extract_input_chars`.
- `apps/api/tests/test_research_agent.py`: mở rộng kiểm tra `VARIANTS` và thêm 3 test đơn vị/tích hợp cho `select_relevant_passages` và `passage_filter`.
- `docs/evaluations/research-agent/README.md`, `docs/stories/optimization-program/design.md`, `docs/stories/optimization-program/validation.md`: cập nhật thiết kế, hợp đồng `passage_filter` và bảng số đo đối chứng 8 câu ngày 2026-11-25.
- `docs/evaluations/research-agent/2026-11-25-reference.json`, `2026-11-25-optimized.json`, `2026-11-25-comparison.md`: lưu artifact chỉ số và hash đã kiểm tra (không chứa toàn văn corpus/bí mật).
- `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, phiên log này.

### Quyết định

- Không thay đổi hành vi `reference`/`naive`, không đổi provider mặc định (`codex` / `gpt-6-luna`), không hạ bất kỳ cổng chất lượng hay đánh dấu hoàn tất sớm story `US-OPTIMIZATION-PROGRAM`.
- Tạm dừng trước khi chạy lượt đo 8 câu thứ hai (~1,1M token Codex) để Linh xác nhận có muốn sửa thêm `stage_searching` (ưu tiên duyệt hit theo hạng thay vì duyệt hết từng truy vấn) rồi đo lại, hay commit/push trước.

### Lệnh & kết quả kiểm chứng

- `bash scripts/bootstrap-harness.sh`, `scripts/bin/harness-cli query matrix --active --summary`, `harness-cli intake` (#38, lane `normal`).
- Kiểm thử tập trung (`tests/test_research_eval.py`, `tests/test_research_agent.py`, `tests/test_research_execution_guards.py`, `tests/test_operations.py`): **115 passed**. `ruff check` & `git diff --check`: sạch.
- `scripts/bin/harness-cli story verify US-OPTIMIZATION-PROGRAM`: **pass** (API **938 passed**, 4 skipped; web **236 passed** / 45 tệp).
- Đo đối chứng đầy đủ **8 câu × 2 biến thể** (Codex `gpt-6-luna`, corpus cố định `research-corpus-20261119.json`, PostgreSQL tách biệt đã xóa sạch `pg_database`, `stop_on_provider_error=True`):
  - Cả 16/16 lượt đều `completed`, 0 lỗi, 0 thiếu usage.
  - Tổng token: **790.441 → 380.987 (−51,8%)** (từng câu giảm từ −29,7% đến −63,4%).
  - Thời gian trung bình: **137,5s → 95,7s (−30,4%)**; số lệnh gọi AI: **70 → 40 (−42,9%)**; ký tự prompt: **1.352.669 → 695.404 (−48,6%)**.
  - Chất lượng trung bình: `citation_coverage` 1,0 vs 1,0; `quote_verification_rate` 0,905 → 0,908; `perspective_coverage` 0,925 → 0,975 (7/8 câu `optimized` đủ 5/5, 0 writer fallback); `sources_cited` 8,875 → 9,625; `entity_recall` 0,400 vs 0,400.
  - `research-eval-compare`: giữ kết luận `Chưa đủ điều kiện kết luận KPI` do 6 mục từng câu (3 câu `reference` và 1 câu `optimized` thiếu 1/5 góc nhìn tại bước trích xuất; `q1`/`q2` giảm 1 thực thể dù trung bình bằng nhau).
- Xác nhận 0 job đang chạy trong 3 hàng đợi (`research_runs=0`, `links=0`, `docs=0`), khởi động lại `worker` và `api`: `GET /api/v1/health` 200, ẩn danh `/api/v1/graph` 401, Web `:13000/graph` 200.

### Vấn đề còn lại & bước tiếp theo

- `US-OPTIMIZATION-PROGRAM` giữ `in_progress` vì cổng từng câu của `research-eval-compare` còn 6 mục (3 từ `reference`, 3 từ `optimized`).
- Bước kỹ thuật tiếp theo (chờ Linh chốt): (1) sửa `stage_searching` duyệt hit theo hạng trước (`rank-first round-robin`) để tránh `market` chiếm hết nguồn đầu bảng của các góc nhìn khác, rồi đo lại đủ 8 câu nếu duyệt quota Codex; hoặc (2) nghiệm thu Weave/Graph v2 và commit/push gói thay đổi hiện tại kèm `.github/workflows/ci.yml`.
