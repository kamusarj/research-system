# Local model audit hardening

## User request

Thực hiện các đề xuất audit và kiểm tra Mistral. Phiên worker này phụ trách bảo mật/timeout model
local, trạng thái form chat và hướng dẫn triển khai. Parent `/root` phụ trách Mistral và bàn giao chung.

## Files changed

- `apps/api/app/services/providers/local_models.py`
- `apps/api/tests/test_local_models.py`, `apps/api/tests/test_ollama_bridge.py`
- `apps/web/app/chat/chat-workspace.tsx`, `apps/web/app/chat/page.test.tsx`
- `apps/web/e2e/local-chat-models.spec.ts`
- `.env.team.example`, README (chỉ phần model local)
- `Docs/Local Model Deployment Plan.md`, `Docs/Team Deployment Runbook.md`

## Decisions made

- Kiểm tra credential sau mỗi tầng JSON decode, kể cả tên thuộc tính, danh mục và arguments JSON.
  Dùng lỗi an toàn và không trả dữ liệu upstream khi bị chặn.
- Async HTTPX có deadline bao cả header/body; giao diện provider đồng bộ giữ nguyên. Nếu caller
  đã có event loop, chạy loop riêng trong worker được join, sao chép contextvars cho số đo/provenance.
- Mở lại cùng form New/Import giữ trạng thái đã kiểm tra; đổi form/provider cần kiểm tra mới.
- Mẫu team nối đúng hai bridge, giữ auth/HTTPS. Recipe SSH chỉ bind đầu tunnel trên loopback.
- Runbook backup cập nhật theo engine chung của worker release; luôn quiesce, manifest/hash,
  retention chỉ nhận dạng backup engine tạo. Không đổi script backup trong worker này.

## Commands/tests run

- `uv run --offline --no-sync pytest tests/test_local_models.py tests/test_local_model_connections.py tests/test_ollama_bridge.py -q`
- `uv run --offline --no-sync ruff check app/services/providers/local_models.py tests/test_local_models.py tests/test_ollama_bridge.py`
- `npm test -- app/chat/page.test.tsx components/chat-local-model-settings.test.tsx`
- `npm run typecheck`, `npm run lint`
- `npx playwright test e2e/local-chat-models.spec.ts --list`
- `git diff --check`

## Verification result

- API 157 test qua; Ruff sạch. Bao gồm real loopback header/body slow-drip: budget 0,2 giây,
  kết thúc trước 0,4 giây và xác nhận socket đóng; escaped-credential ở các tầng JSON bị chặn.
- Web 30 test qua; typecheck/lint sạch sau khi worker release cập nhật dependency.
- Browser fixture đã mở rộng; chạy browser thật do parent thực hiện, ghi evidence ở validation chung.
- Kiểm tra mẫu team bằng Compose JSON thực: API/worker nối URL bridge, auth Secure giữ nguyên,
  bridge không public ports/source mount.

## Known issues

- Chưa có model local cài sẵn hoặc SSH/VPN thật để nghiệm thu; không tải model trong phiên này.
- Independent review release chưa thấy blocker nguồn mới. Cần cài lại script timer ngoài repo
  để timer cũng dùng project lock mới, tránh chồng backup thủ công và định kỳ; đã báo parent.
- Warning Starlette TestClient/httpx và Vitest config loader không làm test fail.

## Next best action

Parent chạy browser với UI mới, tổng hợp regression/Mistral evidence và cập nhật HANDOFF/TASKS/Harness.

## Follow-up: DNS deadline and failed-response usage

Theo review độc lập, `asyncio.run` còn chờ executor DNS khi đóng loop. Đã đổi sang
`asyncio.Runner` với loop riêng, chỉ thay getaddrinfo của loop đó. Resolver có đúng 2 worker và
semaphore 2 slot; OS DNS chưa kết thúc có thể giữ slot, nhưng request đã hủy không mở HTTP/inference
sau đó. Không sửa DNS toàn tiến trình hay URL/Host/TLS/SNI của HTTPX.

`apps/api/app/services/ai.py` bỏ ghi usage trễ ở wrapper; structured local adapter ghi usage ngay
sau HTTP JSON payload và trước kiểm tra content/schema. Thành công/thất bại parse tính đúng một
lần; graph chat giữ hợp đồng trả usage để caller ghi, tránh cộng đôi. Phản hồi bị chặn credential
ngay trong transport chưa cung cấp usage; số đo thiếu được ghi rõ và cổng KPI từ chối kết luận.

Kiểm chứng bổ sung:

- `uv run --offline --no-sync pytest tests/test_local_models.py tests/test_local_model_connections.py tests/test_ai_usage.py tests/test_ai_collector.py -q`: **136 test qua**.
- Ruff các file local_models/ai/test_local_models sạch; `git diff --check` đạt.
- DNS stall: budget 0,08 giây kết thúc trước 0,3 giây; yêu cầu thứ ba không tạo thêm resolver khi
  hai slot đang treo; DNS hoàn thành muộn không gọi HTTP.
- HTTPS loopback thực với certificate test xác nhận Host và SNI vẫn là hostname gốc,
  `CERT_REQUIRED` và hostname verification bật.
- Parent báo browser mở rộng **6/6 qua**, đã cài lại timer mới và đã diễn tập backup/restore.
- Review chất lượng phát hiện per-question provider/model mismatch và NaN metric có thể lọt cổng
  KPI; đã báo worker quality sửa trực tiếp. Không sửa file quality trong worker này.

Source Python đã được đóng băng trước khi parent bắt đầu cặp eval 8 câu; chỉ bổ sung test/log sau đó.
