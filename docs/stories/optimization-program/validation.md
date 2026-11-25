# Validation

## Proof Strategy

Mỗi commit: test API + web hiện có pass, test mới cho phần thay đổi. Bảo mật: npm audit,
pip-audit, gitleaks = 0. Research: eval 8 câu hỏi (`reference` và `optimized`). UI: Lighthouse + ảnh
chụp trước/sau.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Prompt layout tách dữ liệu; usage capture; verifier khớp trích dẫn; validator `[n]`; dedup |
| Integration | Run end-to-end với provider/SearXNG giả; RBAC; Host/Origin 403; rate limit |
| E2E | `/research/new` → báo cáo; dark mode; điều hướng bàn phím; 3 viewport |
| Platform | Compose cục bộ + team overlay; bind 127.0.0.1 |
| Performance | Lighthouse 7 route; thời gian/token eval; token chat trước/sau |
| Logs/Audit | Không log nội dung/PII/secret; audit event cho run |

## Fixtures

- `apps/api/app/evaluation/research_eval_v1.json` (8 câu hỏi Business AI Agents).
- Trang HTML chứa prompt injection cho test.

## Commands

```text
cd apps/api && uv run --frozen python -m pytest -q && uv run --frozen ruff check .
cd apps/web && npm run typecheck && npm run lint && npm test
```

## Acceptance Evidence

2026-10-24 (chi tiết: `AI_LOGS/SESSIONS/2026-10-24-0052-optimization-audit.md`):

| Tiêu chí | Trước | Sau | Đạt |
|---|---|---|---|
| Thời gian 1 research task (eval 8 câu) | naive 135 giây | optimized 80 giây (−41%) | Có |
| Token/chi phí | naive 55,8K/lượt; chat 13,8K ký tự/lượt gọi | optimized 79,4K (+42%, có kiểm tra suy luận); chat −16% | Chưa |
| Claim có nguồn kèm link | không có luồng báo cáo | 100% câu (8/8 lượt, kiểm tra cứng) | Có |
| Lighthouse ≥ 90 | mobile Perf 77–93 | mobile ≥90 trừ /chat 81; desktop ≥94; A11y 94–100 | Gần đạt |
| Lỗ hổng Critical/High | 1 Critical + nhiều High | npm/pip audit 0; review High đã sửa | Có |
| Secret trong repo/lịch sử | 0 | 0 + hook pre-commit + CI | Có |
| Test | API 460, web 180 | API 541, web 192, bot 56 | Có |

## Follow-up 2026-11-03

Local readiness đóng các khoảng trống vận hành/security/UI: bridge ngoài repo và scoped keyring,
Codex native tool-off canary, local auth/owner, backup timer và restore, non-root containers.
Chat mobile production authenticated đạt 91/91/92 (median91), A11y98, first-load JS189→146kB.
API/Discord pip-audit0; npm production0, full audit14 Moderate dev/lint và0 High/Critical.

Verifier batch40/shared evidence/cache verdict24h: benchmark native40 claim giảm54,7% token,
40/40 verdict đúng; replay8 run giảm0,88% payload chars. Một q2 thật completed với23 verified claim,
18 câu có citation/9 nguồn; không đủ để xác nhận KPI chi phí toàn pipeline. Giữ story in_progress
cho mục giảm20% token/chi phí trên eval8 câu cùng provider/config và nghiệm thu còn mở.
Evidence: `docs/evaluations/local-readiness/README.md`, story `remaining-local-readiness`.

## Kiểm chứng công cụ đánh giá đối chứng

- Cặp đủ điều kiện gồm `reference` rồi `optimized`, mỗi biến thể có đúng cờ pipeline và cả hai
  dùng cùng corpus cố định có checksum. Artifact cũ hoặc khác cấu hình vẫn xem được bảng chẩn đoán.
- `--stop-on-provider-error` lưu đầy đủ chi phí các câu đã thử rồi trả mã thoát `2` nếu phải
  dừng. Kiểm thử xác nhận câu tiếp theo được bỏ qua khi bật cờ và vẫn chạy theo mặc định.
- Ngày 2026-11-25, 114 ca kiểm thử tập trung đạt. Harness verify đạt với API 933 ca (4 bỏ qua)
  và web 236 ca. `q1-market-size` hoàn tất trên cả hai biến thể
  bằng Codex `gpt-6-luna` với cùng corpus trên PostgreSQL tách biệt. Mỗi lượt có tám lần gọi và
  đủ usage. Độ phủ trích dẫn đạt 100% và độ phủ góc nhìn đạt 80% ở cả hai lượt, dưới ngưỡng
  100%. Trình so sánh ghi nhận thiếu cổng góc nhìn và chưa chạy đủ tám câu. Database thử đã xóa.

### Truy nguyên độ phủ theo góc nhìn

- Đo lại `q1-market-size` trước sửa bằng cùng corpus và Codex `gpt-6-luna`. `reference` đạt 5/5
  góc nhìn, `optimized` đạt 2/5. Lượt `optimized` có 2 nguồn đọc được cho góc nhìn đối thủ, nhưng
  không trích xuất nhận định nào thuộc góc nhìn đó. Writer bỏ mục kỹ thuật và rủi ro dù có lần
  lượt 3 và 4 nhận định đã kiểm chứng. Hai lượt đều đạt 100% độ phủ trích dẫn và có đủ usage.
- Regression kiểm tra việc bổ sung mục bằng nguyên văn một nhận định đã kiểm chứng và vẫn hiển
  thị khoảng trống thật khi thiếu nhận định. Kết quả JSON của từng câu ghi riêng góc nhìn có
  nhận định đã kiểm chứng, góc nhìn xuất hiện và mục được bổ sung.
- Sau sửa, cả hai biến thể `q1-market-size` đạt 5/5 góc nhìn, 100% độ phủ trích dẫn, 40% độ phủ
  thực thể và đủ usage. `optimized` có nhận định đã kiểm chứng cho cả năm góc nhìn, trong đó
  máy chủ bổ sung mục đối thủ và kỹ thuật. Comparator còn một lý do chặn vì chưa đủ tám câu.
  Kiểm thử tập trung 112 ca đạt. Harness verify đạt với API 935 ca (4 bỏ qua) và web 236 ca.

### Lọc đoạn nguyên văn và đo đối chứng đủ 8 câu (2026-11-25, intake 38)

- Phân tích offline corpus cố định 158 nguồn (`research-corpus-20261119.json`) cho thấy `dedup`
  loại 0 nguồn (0 bản sao gần giống, tối đa 3 nguồn/domain) và `llm_cache` lạnh 0 hit nên trước
  đây `reference` và `optimized` gửi cùng lượng ký tự trích xuất (~150–176K ký tự/câu).
- Đã thêm `select_relevant_passages` (chọn đoạn nguyên văn theo offset `(start, end)`, 5.000 ký
  tự/nguồn, tối đa 6 nguồn/lô) bật riêng cho `optimized` (`passage_filter=True`; `reference` và
  `naive` giữ `passage_filter=False`, không đổi baseline hay verification) và làm rõ `WRITE_TASK`
  (`research-write-v3-all-perspectives`) cho cả hai biến thể.
- Kiểm thử: 115 ca tập trung + `ruff` + `git diff --check` đạt; `harness-cli story verify
  US-OPTIMIZATION-PROGRAM` đạt (API **938 passed**, 4 skipped; web **236 passed** / 45 tệp).
- Đo đối chứng đầy đủ **8 câu × 2 biến thể** (Codex `gpt-6-luna`, effort `low`, cùng mã nguồn
  `source_sha256=292d649e...`, cùng corpus `014428db...`, PostgreSQL tách biệt đã xóa,
  `stop_on_provider_error=True`). Artifacts chỉ số/hash tại
  `docs/evaluations/research-agent/2026-11-25-{reference.json,optimized.json,comparison.md}`:

| Chỉ số (8 câu) | `reference` | `optimized` | Chênh lệch thực tế |
| --- | ---: | ---: | ---: |
| Hoàn tất / thiếu usage | 8/8 (`0` thiếu) | 8/8 (`0` thiếu) | 0% |
| Tổng token | 790.441 | 380.987 | −51,8% |
| Tổng ký tự prompt | 1.352.669 | 695.404 | −48,6% |
| Số lượt gọi AI | 70 | 40 | −42,9% |
| Thời gian trung bình (giây) | 137,525 | 95,688 | −30,4% |
| Độ phủ trích dẫn | 1,000 | 1,000 | 0% |
| Tỉ lệ khớp trích dẫn | 0,905 | 0,908 | +0,3% |
| Nguồn / domain trích dẫn TB | 8,875 / 8,500 | 9,625 / 9,125 | +8,5% / +7,4% |
| Độ phủ góc nhìn TB | 0,925 (5/8 đủ 5/5) | 0,975 (7/8 đủ 5/5) | +5,4% |
| Độ phủ thực thể TB | 0,400 | 0,400 | 0% |
| Mục rơi vào writer fallback | 1/8 câu (`q1`) | 0/8 câu | 0 fallback |

- Kết luận cổng KPI nghiêm ngặt (`research-eval-compare`): **Chưa đủ điều kiện kết luận KPI**
  (giữ nguyên cổng nghiêm ngặt, không hạ chuẩn) vì 6 mục ở mức từng câu:
  - Thiếu 1/5 góc nhìn tại bước trích xuất ở 3 câu `reference` (`q1` thiếu `competitors`, `q5`
    thiếu `use_case`, `q6` thiếu `competitors`) và 1 câu `optimized` (`q8` thiếu `competitors`).
    Nguyên nhân truy nguyên: `stage_searching` duyệt hết 8 hit của từng truy vấn theo thứ tự nên
    `market` chiếm các URL tốt trước khi các góc nhìn sau nhận hit hạng 1.
  - Độ phủ thực thể giảm 1 thực thể (`0,4 → 0,2`) ở `q1` và `q2` (bù lại `optimized` tăng `0,2 →
    0,4` ở `q5` và `0,4 → 0,6` ở `q6`, trung bình giữ nguyên `0,400`).
- Story `US-OPTIMIZATION-PROGRAM` tiếp tục giữ `in_progress` chờ xác nhận sửa `stage_searching`
  (rank-first round-robin) và đo lại nếu chủ sở hữu duyệt hạn mức Codex.

### Cân bằng `stage_searching` rank-first round-robin và đo lại 8 câu (`r2`, intake 39)

- Đã sửa `stage_searching` duyệt hit đạt ngưỡng liên quan theo hạng trước (`rank-first round-robin`),
  đặt `EXTRACT_PASSAGE_MAX_CHARS = 5200`, `MAX_EXTRACT_SOURCES_PER_BATCH = 4` và cập nhật
  `EXTRACT_TASK` (`research-extract-v3-grounded-entities`) cho cả hai biến thể.
- Kiểm thử: 116 ca tập trung, `harness-cli story verify US-OPTIMIZATION-PROGRAM` đạt (API **939
  passed**, 4 skipped; web **236 passed** / 45 tệp), Discord bot **56 passed**, Web `eslint`/
  `typecheck`, `verify_second_audit_remediation.sh` và 3 cấu hình Compose CI đều đạt.
- Đo đối chứng đủ **8 câu × 2 biến thể** (`r2`, Codex `gpt-6-luna`, `source_sha256=ebe68beb...`,
  corpus `014428db...`, PostgreSQL tách biệt đã xóa). Artifacts chỉ số/hash tại
  `docs/evaluations/research-agent/2026-11-25-r2-{reference.json,optimized.json,comparison.md}`:

| Chỉ số (8 câu `r2`) | `reference` | `optimized` | Chênh lệch thực tế |
| --- | ---: | ---: | ---: |
| Hoàn tất / thiếu usage | 8/8 (`0` thiếu) | 8/8 (`0` thiếu) | 0% |
| Tổng token | 897.992 | 481.846 | −46,3% |
| Tổng ký tự prompt | 1.395.083 | 757.697 | −45,7% |
| Số lượt gọi AI | 71 | 48 | −32,4% |
| Thời gian trung bình (giây) | 142,162 | 113,513 | −20,2% |
| Độ phủ trích dẫn | 1,000 | 1,000 | 0% |
| Độ phủ góc nhìn (tất cả 16/16 lượt) | **1,000 (8/8 đủ 5/5)** | **1,000 (8/8 đủ 5/5)** | **0% (100%)** |
| Tỉ lệ khớp trích dẫn | 0,904 | 0,897 | −0,8% |
| Độ phủ thực thể TB | 0,400 | **0,450** | **+12,5%** |

- Kết quả cổng nghiêm ngặt (`research-eval-compare`): mọi cổng hoàn tất, usage, trích dẫn và góc
  nhìn (**16/16 lượt đủ 5/5 góc nhìn**) đều đạt; chỉ còn 2 điểm lệch 1 thực thể ở mức từng câu
  (`q6-roi` và `q8-sme-vietnam`: `0,6 → 0,4`, trong khi `optimized` vượt `reference` ở `q1`, `q5`,
  `q7` và trung bình tăng từ `0,400 → 0,450`). Giữ nguyên chuẩn không hạ cổng; `US-OPTIMIZATION-PROGRAM`
  tiếp tục `in_progress`.
