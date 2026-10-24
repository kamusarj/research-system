# Exec Plan — Chương trình tối ưu toàn diện (US-OPTIMIZATION-PROGRAM)

## Goal

Nâng chất lượng/hiệu năng research, UI/UX và bảo mật theo tiêu chí đo được: thời gian research
task −30%, token −20%, 100% claim trong báo cáo có nguồn kèm link, Lighthouse Performance và
Accessibility ≥ 90, 0 lỗ hổng Critical/High, 0 secret trong repo và lịch sử, test cũ vẫn pass.

## Scope

In scope:

- Vá dependency Critical/High; bind cổng cục bộ 127.0.0.1 + bật đăng nhập cục bộ; Host/Origin
  check; pre-commit quét secret.
- Đo usage token/độ trễ AI; chuẩn hóa prompt (tách chỉ dẫn và dữ liệu không tin cậy); giảm ngữ
  cảnh chat; bỏ lời gọi thừa khi xử lý tài liệu; cache LLM/embedding.
- Pipeline mới "câu hỏi → báo cáo có trích dẫn" (planner → searcher → verifier → writer) dùng
  SearXNG tự host + kho nội bộ; bộ eval 8 câu hỏi; skill nhóm.
- Design token + dark mode, primitive dùng chung, tiến độ từng bước, trình đọc báo cáo có
  trích dẫn bấm được, mobile nav.
- Bảo mật Medium/Low còn lại (rate limit AI, ngân sách, SSRF ghim IP, CSP, container non-root).

Out of scope:

- Nâng Next.js lên 16; đổi cơ sở dữ liệu; Discord gateway thật; production MinIO.

## Risk Classification

Risk flags: Auth, Authorization, Data model, Audit/security, External systems, Public contracts,
Existing behavior, Multi-domain.

Hard gates: Auth (bật đăng nhập cục bộ), Data model (bảng mới, migration additive),
Audit/security, External provider behavior (SearXNG, prompt).

## Work Phases

1. Discovery: audit 2026-10-24 (`AI_LOGS/SESSIONS/2026-10-24-0052-optimization-audit.md`).
2. Design: `design.md`.
3. Validation planning: `validation.md`.
4. Implementation: mỗi cải tiến một commit; bảo mật Critical/High trước.
5. Verification: test + eval sau mỗi commit; revert nếu không cải thiện.
6. Harness update: decision 0051, AI_LOGS.

## Stop Conditions

Pause for human confirmation if:

- Cần xóa dữ liệu/file, đổi interface công khai đang dùng, tăng chi phí API, hoặc đổi cơ chế
  đăng nhập ngoài phạm vi đã duyệt.
- Validation requirements need to be weakened.
