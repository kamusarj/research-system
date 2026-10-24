# Validation

## Proof Strategy

Chứng minh khóa đúng đi tới đúng provider instance, không còn trong dữ liệu durable,
request errors hoặc response, không thay global key và thiếu key personal không fallback.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit/integration | Personal create/send/import; model pinning; mixed users/keys; missing/invalid key; system unchanged; auth/CSRF; provider HTTP failures |
| Database | SQLite migration upgrade/downgrade/upgrade, PostgreSQL upgrade/check |
| Frontend | Password entry, memory-only retention, clear/reset, personal provider availability, key transmission |
| E2E | Personal create/send/reload and responsive settings plus existing chat flows |
| Runtime | API/frontend health, actual migration head, no unrelated containers changed |

## Fixtures

Synthetic non-production keys and mocked HTTP provider responses. No paid provider calls.

## Acceptance Evidence

- Hoàn tất: Ruff, 334/334 API tests; 54 kiểm thử tập trung personal/chat/import/auth.
- 14/14 unit frontend, TypeScript và ESLint đạt; production build Next.js 15 route đạt.
- 12/12 Playwright trên dev và production: chat cũ + personal create/send/reload qua ba viewport.
- SQLite migration upgrade/check/downgrade/upgrade đạt. PostgreSQL lên `3e5f7a9b1c24`;
  `alembic check` sạch sau khi gắn đúng tên hai PaperEvaluation check constraints có sẵn
  vào ORM. Biểu thức điều kiện và ràng buộc database không bị thay đổi.
- Dữ liệu thật trước/sau: 10 sessions, 32 messages, 10 sessions cũ dùng system.
- API/frontend restart riêng, health thành công; worker/database/Smart Exam giữ nguyên.
- Key tests chỉ dùng synthetic fixtures và mock HTTP; không gọi AI có phí hoặc lưu khóa thật.
