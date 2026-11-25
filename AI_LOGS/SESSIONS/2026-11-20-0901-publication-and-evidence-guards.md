# Publication and evidence guards

## User request

Chủ sở hữu yêu cầu bắt đầu sửa các phát hiện audit tiếp theo. Worker này xử lý ba lỗi quyền tài
liệu/quan hệ và giữ bằng chứng canonical, thuộc intake21 / `US-SECOND-AUDIT-REMEDIATION` / decision0057.
Parent quản lý HANDOFF, TASKS và proof Harness chung.

## Files changed

- `apps/api/app/services/research.py`: cổng quyền sửa nghiên cứu tại service, dùng lại cho update và
  cả hai đầu quan hệ.
- `apps/api/app/api/research.py`: bỏ cổng quyền trùng ở controller, gọi service đã bảo vệ.
- `apps/api/app/services/document_editing.py`: kiểm tra quyền trước version/restore/AI accept và
  trước ghi object/metadata.
- `apps/api/app/services/documents.py`: chặn xóa nếu còn bằng chứng canonical hoặc mutation đã áp
  dụng tham chiếu evidence/nút/cạnh tài liệu, không phụ thuộc origin document/chat.
- `apps/api/tests/test_review_boundaries.py`: 34 ca hồi quy hành vi và side effect.

## Decisions made

- Giữ chính sách0048: chỉ owner sửa research `in-review`/`approved`; researcher vẫn sửa bản nháp.
  Khi thêm quan hệ, cả hai đầu phải cho phép sửa theo cùng chính sách để không xuất bản cạnh bằng
  đường vòng. Không tự đổi trạng thái hay tạo approval giả.
- Cổng version nằm ở service trước storage.put; restore/accept cũng kiểm tra trước đọc/thay đổi.
  `update_research` dùng chung cổng để mọi caller được bảo vệ.
- Giữ chính sách0042: canonical node/edge evidence và accepted mutation thuộc bất kỳ change set
  `applied` nào giữ nguồn. Bao gồm ADD_ALIAS không sao chép evidence, và provenance của bản sao cũ
  thiếu `source_document_id`. Giữ lỗi409 `DOCUMENT_DELETE_PROVENANCE_LOCKED`.
- Draft/rejected mutation không giữ tài liệu; hành vi owner xóa tài liệu chưa được áp dụng vẫn
  hoạt động. Không sửa schema hoặc đụng migration lease của worker khác.

## Commands/tests run

```text
cd apps/api
uv run --offline --no-sync pytest tests/test_review_boundaries.py -q --tb=short --maxfail=1
uv run --offline --no-sync pytest tests/test_review_boundaries.py tests/test_auth.py tests/test_document_editing.py tests/test_documents.py tests/test_research.py tests/test_graph_changes.py -q --tb=short
uv run --offline --no-sync ruff check app/services/research.py app/api/research.py app/services/document_editing.py app/services/documents.py tests/test_review_boundaries.py
git diff --check
```

## Verification result

- 34 ca mới qua: 15 ca version/restore/AI accept theo role/trạng thái; 12 ca quan hệ; 7 ca giữ nguồn.
- Tổng kiểm thử liên quan **97 passed**; Ruff sạch; diff check đạt.
- Khi bị từ chối: storage.put/delete không được gọi; object bytes, version, content, proposal và
  audit giữ nguyên. Owner và thao tác trên bản nháp có kiểm chứng thành công.
- Bằng chứng canonical node/edge, copied provenance cũ, applied chat alias/source-node đều chặn
  xóa; draft/rejected alias cho phép xóa nguồn mà không xóa node canonical.
- Các fixture ban đầu thiếu cờ cookie HTTP/type bắt buộc đã được sửa; kết quả cuối ở trên.

## Known issues

- Không dùng model thật hoặc xóa dữ liệu thật để thử. Test DB SQLite trong bộ nhớ và storage tạm.
- Warning Starlette TestClient/httpx hiện có không làm kiểm thử fail.
- Full suite, migration PostgreSQL nếu cần lease token, và refresh runtime do parent tổng hợp sau
  khi các worker khác hoàn tất. Không tự ghi product acceptance hoặc KPI20%.

## Next best action

Parent hoặc worker rảnh review diff, chạy proof chung và cập nhật HANDOFF/TASKS/Harness.

## Follow-up sau review độc lập

Worker release phát hiện đường thêm attachment còn ghi metadata của research đã duyệt và race
publish trong lúc await storage.put. Parent yêu cầu sửa cùng chính sách hiện hành:

- Attachment chuyển qua `services.research.create_attachment`, kiểm tra cùng owner gate trước ghi.
- Sau storage.put, version service đọc lại ResearchItem bằng `populate_existing` + `FOR UPDATE`
  dưới `no_autoflush`, kiểm tra quyền lại rồi mới sửa metadata/version. Chỉ giữ khóa trong đoạn ghi
  DB ngắn, không qua thao tác object storage. Khi bị từ chối, rollback trước rồi xóa object mới chưa
  được gắn; không đổi approval API hoặc thêm điều kiện ETag.
- Thêm 5 ca attachment theo role/trạng thái và 3 ca owner publish bằng callback trong storage.put
  (version/restore/AI accept): mỗi ca trả403, giữ source version/content/proposal, xóa đúng object mới.

Kết quả cuối worker: **42 ca mới**, **105 kiểm thử liên quan qua**, Ruff các5file sạch và diff check đạt.

Review độc lập phần search/limiter của parent không thấy blocker; mô phỏng20.000 thao tác limiter
khớp reference và hết hạn thu hồi đủ map/heap. Đã đọc lease/verifier/cache/report/CPU của worker
quality: chưa thấy blocker nguồn mới; root kiểm chứng PostgreSQL thực riêng. Các review này chỉ đọc,
không sửa source ngoài phạm vi worker.
