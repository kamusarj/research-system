# Audit remediation — 2026-11-19

## Kiểm chứng triển khai

- Harness proof:809 API tests,226 web tests/44 files,56 bot tests; Ruff/ESLint/TypeScript/lock/shell đạt.
- Browser6/6 trên UI production, hai local protocol × desktop/tablet/mobile, New/Import lặp lại.
  Request model là fixture; không coi là model/SSH thật.
- PostgreSQL smoke trên DB rỗng riêng: upgrade/check/downgrade1/reapply/check đạt, DB thử đã xóa.
- Backup/restore thật46 bảng; archive4 object,2 object local tham chiếu, thiếu0, lệch hash phiên bản0.
  Timer dùng cùng bản script mới với lock chung; tự phát hiện env nhóm tôn trọng Compose project.
- Runtime UI: Node22.23.2, Next15.5.29, dependency fingerprint, health200. npm full/production audit0.
- DNS deadline được tái hiện độc lập: budget0,1s trước sửa0,700s; sau sửa0,102s. DNS pool giới hạn2
  worker mỗi tiến trình; kết quả DNS muộn không tiếp tục HTTP. HTTPS giữ Host/SNI/certificate check.

## Mistral API thật

[Artifact an toàn](2026-11-19-mistral.json): danh mục200; `mistral-embed` trả vector hợp lệ1024 chiều.
`mistral-large-latest`403/tier_not_allowed/code1910 và không nằm trong danh mục của key. Medium/Small
trả429; thử Small tuần tự và thử lại sau thời gian chờ dài vẫn429. Không suy số dư hoặc đổi model/
provider mặc định. Chưa thể dùng generation với credential/tier/rate limit hiện tại; embedding hoạt động.

Đối chiếu giao thức: [Mistral Chat](https://docs.mistral.ai/api/endpoint/chat),
[Embeddings](https://docs.mistral.ai/api/endpoint/embeddings).

## Đối chứng nghiên cứu thật

8 câu hỏi chuẩn, provider Codex/gpt-6-luna/effort low, cùng cấu hình và corpus công khai158 nguồn;
DB PostgreSQL riêng, cache salt riêng cho mỗi variant. Không dùng kho nội bộ. Corpus0600 ngoài repo;
artifact chỉ có chỉ số, config allowlist và hash. `naive` lịch sử giữ nguyên; dùng `reference` có
entailment để đối chứng với `optimized`.

- [Reference8 câu](2026-11-19-reference.json): completed8/8,70 calls,870579 tổng token;
  citation coverage1,0, perspective coverage trung bình0,7. Không đủ quality gate để kết luận KPI.
- [Optimized8 câu](2026-11-19-optimized.json): completed5/8; q6-roi/q7-finance-ops/q8-sme-vietnam
  thất bại `AI_RESPONSE_INVALID` (usage_missing 18 lượt gọi); 62 calls,415823 tổng token trên mọi
  lượt đã thử; citation coverage1,0, quote verification0,925, perspective coverage trung bình0,72.
- [Đối chiếu reference↔optimized](2026-11-19-comparison.md): **chưa đủ điều kiện kết luận KPI**.
  Cổng chất lượng per-run (trích dẫn/góc nhìn) không đạt ở q1/q3/q4/q5; q6/q7/q8 chưa hoàn tất,
  thiếu usage và giảm entity recall. Tổng token thô giảm52% nhưng không được dùng làm kết luận
  KPI20% vì completion rate rơi xuống0,625 và quality/usage gates chưa đạt.
- Kết luận quality gates: **KHÔNG ĐẠT** cho KPI giảm20% toàn pipeline. Ba câu optimized thất bại
  (`AI_RESPONSE_INVALID`) là lỗi thật cần xử lý trước khi đo lại; không loại chúng khỏi số liệu.

Codex CLI trong lần đo cung cấp tổng token cho mọi call nhưng không có input/output/cached split
(đã kiểm tra cột metric gốc). Các số0 ở input/output trong artifact là trường cộng dồn mặc định khi
chưa có số đo, không phải bằng chứng model dùng0 input/output token. Chỉ dùng tổng token để đánh giá;
không quy thành chi phí tiền. Latency replay không bao gồm SearXNG/live web và không đại diện deploy nhóm.

## Giới hạn còn lại

Root còn dưới1GiB, chưa cài local model/kiểm SSH thật. Chưa có domain nhóm. CI được kiểm local,
chưa commit/push/chạy GitHub. KPI giảm20% toàn pipeline chỉ đạt khi mọi cổng chất lượng đều đạt;
không lấy giao những câu thành công để che phần thiếu.
