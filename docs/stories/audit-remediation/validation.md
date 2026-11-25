# Validation

## Proof Strategy

Regression tái hiện lỗi trước đây, toàn bộ API/web/bot và kiểm tra cấu hình triển khai.

| Layer | Cases |
| --- | --- |
| Unit | Negation/entity/appended claim, failed usage, eval failures/manifest, JSON-escaped credential |
| Integration | Header/body slow-drip deadline, backup quiesce/resume/failure, lockfile refresh |
| E2E | Trạng thái local picker khi tạo/import lặp lại; không đổi quyền/auth |
| Platform | Compose base/team, PostgreSQL migration + alembic check, dependency audit |
| Live provider | Mistral models, bounded synthetic structured/chat/embedding request; no secrets logged |

## Acceptance Evidence

2026-11-19, bằng chứng hiện có:

- API full809 tests và Ruff đạt trong Harness story proof (sau test TLS và project backup mới).
  Web44 file/226 tests, ESLint/TypeScript; bot56/Ruff đạt. `story verify` đạt.
- Playwright local-models6/6 trên UI production: desktop/tablet/mobile × hai protocol, cả New/Import
  mở lặp lại sau probe, pin model và chặn browser gọi cổng model trực tiếp. Đây là network fixture,
  không phải nghiệm thu model thật.
- Header/body/DNS stall có regression deadline; DNS pool tối đa2, DNS muộn không tiếp tục inference.
  HTTPS loopback chứng minh giữ Host/SNI/certificate verification. JSON escape/property/tool/catalogue
  không lọt khóa cấu hình. Structured parse failure vẫn cộng usage đo được, không cộng đôi.
- PostgreSQL16/pgvector hiện có, DB rỗng riêng `baa_ci_*`: upgrade/check/downgrade1/reapply/check đạt.
  Không migration DB ứng dụng; database thử đã xóa.
- Backup thật bằng engine mới, restore DB tách biệt46 bảng: archive4 object,2 tham chiếu local,
  thiếu0, hash phiên bản lệch0; checksum manifest đạt. Database restore thử đã xóa. Timer đã nhận
  script dùng lock chung; không thực hiện concurrent delete trên dữ liệu thật (race có regression).
- Dependency volume đã đồng bộ/build/recreate UI: Node22.23.2, Next15.5.29, marker fingerprint tồn tại,
  API/UI health200. npm audit full/production đều0; không nâng major. Build rollback lưu ngoài repo.
- Mistral live: danh mục200, embedding hợp lệ1024 chiều; model Large403 `tier_not_allowed`,
  Medium/Small429 và thử tuần tự lại Small vẫn429. Không đổi provider/model mặc định.
  Artifact: `docs/evaluations/audit-remediation/2026-11-19-mistral.json`.
- Paired eval thật8 câu reference/optimized hoàn tất với Codex, corpus158 nguồn công khai cố định,
  database riêng đã tự xóa; chỉ xuất chỉ số/hash. Reference 8/8 completed (870579 token,70 calls);
  optimized 5/8 (q6/q7/q8 `AI_RESPONSE_INVALID`, usage_missing 18; 415823 token,62 calls).
  `research-eval-compare` kết luận **chưa đủ điều kiện kết luận KPI**: q1/q3/q4/q5 hụt cổng
  perspective per-run, q6/q7/q8 chưa hoàn tất + entity recall giảm. Artifacts:
  `docs/evaluations/audit-remediation/2026-11-19-{reference,optimized,comparison}.{json,json,md}`.
  Corpus nằm ngoài repo0600; không dùng kho nội bộ.

KPI giảm20% token vẫn mở đến khi đủ quality gates; tổng token thô giảm52% không được dùng kết luận
khi completion rate0,625 và quality/usage gates chưa đạt. Ba câu optimized thất bại là lỗi thật cần
xử lý trước khi đo lại. SSH/local model thật, HTTPS nhóm và GitHub CI không được tuyên bố đạt bằng
fixture/local checks. Root còn khoảng580MiB; không tải model/build ảnh lớn.
