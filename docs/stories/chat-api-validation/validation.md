# Validation

## Proof Strategy

Fixtures tổng hợp và mock HTTP; không dùng khóa thật hoặc gọi inference có phí.

## Test Plan

| Layer | Cases |
| --- | --- |
| API | Dynamic models, model probe, malformed responses, distinct 401/402/403/404/429/400/422/5xx, timeout, redaction, no persistence |
| Security | Required SecretStr, provider allowlist, auth roles, CSRF, rate limits, no fallback |
| Frontend | Select flow, failed validation prevents save, key/provider/model invalidation, stale/unmount protection, pinned old model |
| E2E | Personal create/send/reload plus error/recovery and existing chat on three viewports |
| Runtime | Type/lint/build, API/frontend health, unrelated containers unchanged |

## Acceptance Evidence

- Ruff toàn API đạt; 380/380 API tests đạt, gồm 46 ca connection mới và 11 ca
  personal API trước đó. Auth/CSRF/rate, secrets/redaction/no persistence được kiểm tra.
- 34 tệp / 171 Vitest đạt; 20 ca settings mới và 8 ca chat page; ESLint/TypeScript đạt.
- Production build Next.js 15 route trong container đạt, không thay dependency/image.
- Playwright dev: 12 ca chat/personal đạt; 3 ca error-flow ban đầu vướng selector alert
  trùng Next route announcer, sửa scope vào form rồi 3/3 đạt. Không đổi hành vi để né test.
- Playwright production: 15/15 đạt trên desktop/tablet/mobile cho graph-chat,
  personal-chat-api và chat-api-validation. Ảnh lỗi/settings đã kiểm tra trực quan,
  không tràn ngang; artifact tổng hợp `/tmp/chat-api-validation-*-chrome.png`.
- API/frontend restart riêng và healthy. Health API `/api/v1/health` và `/chat` HTTP
  200; hai endpoint mới và proxy từ chối body thiếu key bằng 422, không gọi upstream.
- Head vẫn `3e5f7a9b1c24`; 10 sessions/32 messages. Worker/database/Smart Exam giữ
  nguyên container ID/uptime. Không migration mới, không gọi key thật, không prune Docker.
- `harness-cli story complete US-CHAT-API-VALIDATION`: pass, 57 tests proof tập trung.

## Gaps

Không đo số dư hoặc xác minh quyền bằng tài khoản thật; upstream được mock theo tài liệu
chính thức. Thành công lúc probe không đảm bảo quyền/credit tương lai. Lỗi và từ chối
provider thực tế vẫn được phân loại cùng đường code. Cảnh báo Starlette/httpx deprecated
và Playwright NO_COLOR/FORCE_COLOR có sẵn không làm thất bại kiểm thử.
