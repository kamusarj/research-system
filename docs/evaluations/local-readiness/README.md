# Local readiness — 2026-11-03

Chỉ lưu số đo và fixture tổng hợp. HTML Lighthouse/cookie/credential/DOM thật không nằm trong repo.

## Chat

Production Next.js, Google Chrome trên máy, Lighthouse mobile có throttling mặc định, owner đã
đăng nhập (`/auth/me` 200), cùng cuộc trò chuyện trước/sau. Không thay dữ liệu chat giữa các lần đo.
Các bản trung gian dùng để chẩn đoán đã bỏ; ba tệp `chat-hydrated-final-*` là mã cuối.

| Chỉ số | Trước | Sau (3 lần) |
| --- | --- | --- |
| Performance | 80 | 91 / 91 / 92 (trung vị 91) |
| Accessibility | 98 | 98 / 98 / 98 |
| LCP | 3,9 giây | khoảng 3,3 giây |
| TBT | 290 ms | 36 / 37 / 33 ms |
| First-load JS `/chat` | 189 kB | 146 kB |

Đo sau bản sửa UTC/server so với timezone browser. Live smoke desktop/tablet/mobile không có
pageerror, không tràn ngang; owner HTML private/no-store, anonymous không nhận session ID và
cookie không được serialize. E2E auth dùng Pacific/Honolulu với fixture 24 tin: ban đầu8,
click đầu fetch lịch sử một lần rồi mở 16, click sau 24 không fetch thêm; không hydration error.
Điểm Lighthouse có dao động; đây là số đo trên máy hiện tại, không phải cam kết trên mọi thiết bị.

## Research

- `verifier-compaction.json`: replay payload8 run có sẵn, giảm0,88% ký tự. Không phải token hay
  chi phí provider, không bỏ cửa sổ bằng chứng.
- `verifier-batching-native.json`: 40 claim tổng hợp qua Codex thật, batch20→40 và shared context:
  2 call/26466 token → 1 call/11995 token (−54,7%); 40/40 verdict đúng ở cả hai.
- `research-smoke.json`: một câu q2 trên pipeline thật với Codex/SearXNG, completed97,7giây,
  8 call/107598 token; 18 câu đều có citation, 9 nguồn/8 domain, 23 claim verified.
  Báo cáo giữ draft. Entity recall0,4; không dùng một mẫu này để kết luận chất lượng toàn bộ8 câu.

Chưa chứng minh KPI giảm20% token **toàn pipeline** so với naive8 câu. Hai benchmark verifier
không thay thế phép so sánh đó. Giữ `US-OPTIMIZATION-PROGRAM` mở cho tiêu chí này.

## Audit và vận hành

- pypdf6.21.4 trên runtime mới; pip-audit API 53 package và Discord lockfile:0 advisory.
- npm production audit0; đầy đủ14 Moderate thuộc lint/dev,0 High/Critical. Không force downgrade.
- Gitleaks lịch sử trước commit:47 commit,0 secret; pre-commit tiếp tục quét phần staged.
- Container canary mới + live API/worker: non-root/read-only/caps, legacy storage/restore, LaTeX/OCR
  và migration đạt. Backup timer đã chạy thử; restore46 bảng và toàn bộ hash tệp khớp trong fixture.

Các lệnh và kết quả browser cuối được ghi trong story validation và session log cùng ngày.
