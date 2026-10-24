# Session: Tối ưu toàn diện research / UI / bảo mật

## Context

- User request: tối ưu toàn diện hệ thống research cho nhóm Business AI Agents theo quy trình Bước 0
  (công cụ) → 1 (audit + baseline) → 2 (kế hoạch, đã duyệt "làm đi") → 3 (triển khai từng cải tiến,
  commit riêng) → 4 (review độc lập, README, báo cáo). Quyết định của Linh: commit snapshot nền;
  web search = SearXNG tự host; bind 127.0.0.1 + bật đăng nhập (đăng nhập để sau, chờ tạo owner);
  dùng quota Codex CLI cho pipeline/eval; cho xóa ảnh Docker `c2-app-047-app`, `aquasec/trivy`.
- Agent: Claude Code (Opus 5.5). Date: 2026-10-24 00:20–19:00 Asia/Bangkok (có quãng dừng do hạn mức).
- Harness: intake #13 high-risk; story `US-OPTIMIZATION-PROGRAM` (in_progress); decision 0051 / DEC-064.

## Work Done

- Commit: snapshot `dce73d7` + 36 commit trên `feature/research-system-mvp` (chưa push).
- Files changed (chính):
  - Research: `apps/api/app/services/research_agent/` (runner, search, evidence, writer, schemas),
    `api/research_runs.py`, `schemas/research_runs.py`, `evaluation/research_agent.py` +
    `research_eval_v1.json`, `services/prompts.py`, `services/ai_usage*.py`, `services/ai_output_guard.py`,
    `core/request_guard.py`, `core/runtime_controls.py`, `services/sources/http.py` + `politeness.py`,
    migrations `4a6c8e0b2d35`, `5b7d9f1c3e46`, `6c8e0a2b4d57`.
  - Web: `app/globals.css` (token, dark mode, CSS tính năng), `app/research/new`,
    `app/research/runs/[id]`, `components/report-markdown.tsx`, `components/research-run/*`,
    `components/theme-toggle.tsx`, `components/app-shell.tsx` (nav + thanh dưới), `lib/auth.tsx`,
    `lib/research-runs.ts`, `next.config.ts` (CSP), `components/knowledge-graph/d3-graph-canvas-lazy.tsx`.
  - Ops/docs: `ops/searxng/settings.yml`, `docker-compose.yml` (SearXNG, bind, biến mới),
    `docker-compose.team.yml` (FORWARDED_ALLOW_IPS), `.githooks/pre-commit`, `scripts/install-git-hooks.sh`,
    `scripts/research-report.sh`, `.github/workflows/security.yml`, `.gitleaks.toml`,
    `.claude/settings.json`, `.claude/skills/research-report`, `.claude/skills/research-eval`, `README.md`,
    `docs/decisions/0051-*.md`, `docs/stories/optimization-program/*`, `docs/evaluations/research-agent/*`.
- Runtime (ngoài repo): `.env` thêm `API_TRUSTED_HOSTS=.trycloudflare.com`, `SEARXNG_SECRET`
  (giá trị không ghi ở đây); ảnh api/worker build lại; SearXNG chạy; migration áp dụng sau pg_dump.

## Reasoning / Decisions

- Pipeline: writer chỉ trả câu + mã nhận định, máy chủ gắn trích dẫn → bảo đảm 100% câu có nguồn bằng
  cấu trúc; thêm kiểm tra từ vựng + suy luận để giảm "dẫn nguồn nhưng nói khác".
- SearXNG: Bing/Mojeek/Startpage trả rác (chỉ khớp từ đầu), Brave/DDG/Google/Qwant chặn IP → dùng
  Yahoo, Yep, Bing News, Mwmbl, HN, Wikipedia, Semantic Scholar, OpenAlex, Crossref, arXiv, GitHub;
  thêm bộ lọc độ liên quan cho kết quả và trang.
- Giữ lô trích 30K (lô 48K giảm token nhưng giảm độ phủ). Giữ bước kiểm tra suy luận dù tốn token.
- Tài liệu "không liên quan" vẫn có đồ thị cấu trúc (giữ cam kết cũ) nhưng bỏ lời gọi AI ngữ nghĩa.
- CSP dùng `'unsafe-inline'` cho script (App Router), không nonce để không ép render động.
- Không đổi sandbox CLI khi chưa kiểm chứng được với CLI thật; thay bằng che chuỗi giống khóa.

## Verification

- Baseline (trước): API 460/460, web 180/180; npm audit 1 Critical + 2 High; pip-audit nhiều advisory;
  Lighthouse mobile Perf 77–93 / A11y 94–100; chat ~13,8K ký tự mỗi lượt gọi; link trung vị 12,6 giây.
- Sau: API 541/541, web 192/192, bot 56/56; ruff/eslint/tsc sạch; npm audit 0; pip-audit 0 (API, bot,
  cả dev); gitleaks lịch sử 0; hook chặn token giả (đã thử).
- Lighthouse cuối (mobile Perf/A11y): / 93/100, /research 93/100, /ingestion 95/96, /graph 92/96,
  /chat 81/98, /documents 90/100, /search 93/94, /research/new 92/100; desktop Perf 99–100.
- Eval thật 8 câu × 2 biến thể (Codex + SearXNG): optimized vs naive thời gian 135→80 giây (−41%),
  citation coverage 1.0/1.0, quote verification 0,88→0,91, cited duplicates 1%→0, perspective coverage
  0,825→0,925, unique domains 8,6→10,4, total tokens 55,8K→79,4K (+42%).
- Kiểm thử trực tiếp: Host lạ 400, POST cross-site 403, tunnel qua cổng gate 200, SSRF tên miền về
  127.0.0.1 bị chặn, 13 trang không vi phạm CSP, ảnh chụp sáng/tối desktop/mobile.
- Review độc lập (subagent): 2 High, 9 Medium, 9 Low → đã sửa H1–H2, M1–M9, L1–L7, L9; L8 ghi nhận.

## Next Agent Notes

- Continue from: TASKS "Tối ưu toàn diện (2026-10-24)".
- Watch out for: đừng restart API khi `research-eval` đang chạy (giết tiến trình eval); Docker trên `/`
  còn ~2 GB; Playwright E2E ghi dữ liệu thật — chạy trên stack thử nghiệm; tunnel cần
  `API_TRUSTED_HOSTS=.trycloudflare.com`.
- Suggested next command: sau khi Linh tạo owner, đặt `AUTH_MODE=local` và
  `RESEARCH_AGENT_ENABLED=true` trong `.env`, rồi
  `COMPOSE_PROJECT_NAME=businessaiagents API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d --no-build --no-deps api worker`.
