# Validation

## Proof Strategy

Mỗi commit: test API + web hiện có pass, test mới cho phần thay đổi. Bảo mật: npm audit,
pip-audit, gitleaks = 0. Research: eval 8 câu hỏi (naive vs optimized). UI: Lighthouse + ảnh
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
