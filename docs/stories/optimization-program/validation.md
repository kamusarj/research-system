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

Ghi sau khi xác minh.
