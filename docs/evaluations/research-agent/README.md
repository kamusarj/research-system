# Đánh giá pipeline nghiên cứu

## Hợp đồng số đo từ 2026-11-19

Artifact mới có `manifest.version=research-eval-v2`. Các trường `input_tokens`, `output_tokens`,
`total_tokens`, `llm_calls`, `prompt_chars` trong `summary` là **tổng của mọi lượt đã thử**,
kể cả thất bại/hủy; `wall_time_s` là trung bình mọi lượt. Chỉ số chất lượng là trung bình các lượt
hoàn tất và luôn đi cùng `completion_rate`. Usage đã nhận trước lỗi parse/validation vẫn được cộng.
`usage_missing_calls` cho biết số lần chưa có đủ số đo; không coi thiếu usage là miễn phí.

Các JSON lịch sử giữ nguyên. `naive` vẫn tắt entailment để bảo toàn baseline lịch sử, vì vậy không
đủ điều kiện tuyên bố tiết kiệm chi phí ở chất lượng tương đương. `reference` giữ entailment, tắt
cache/khử trùng/song song/lọc đoạn (`passage_filter=False`); đây là đường cơ sở cho lần đo mới với
`optimized` (`passage_filter=True` chọn đoạn nguyên văn giàu thông tin cho bước trích xuất trong
khi giữ nguyên đối chiếu trích dẫn và entailment trên toàn văn nguồn gốc).

Writer hiện chỉ chọn/thứ tự claim: máy chủ dựng nguyên văn từng claim đã kiểm chứng, mỗi claim
đi cùng nhóm trích dẫn riêng. Không dùng độ trùng từ hay sự hiện diện của link để chứng minh
một câu được viết lại đúng nghĩa. Tiêu đề lấy từ câu hỏi người dùng; báo cáo vẫn là nháp.

## Corpus nguồn cố định

Để tái lập so sánh, giữ toàn bộ nguồn công khai trong một tệp bên ngoài repository/AI_LOGS, mode
0600. `write_corpus_from_runs(db, path, {question_id: run_id})` có thể xuất các nguồn HTTP(S) đã
đọc từ lượt `research-eval` có sẵn, không gọi model và không sửa DB. Nguồn kho nội bộ bị loại.
Tệp tạo độc quyền, không ghi đè; checksum và giới hạn kích thước/số lượng/nội dung được kiểm tra.

Hoặc `--capture-corpus /tmp/research-public-corpus.json` ghi nguồn công khai sau một lần đánh giá
thật. Lần thu thập này không phải một trong hai lần đo đối chứng. Cả hai lần đo phải dùng cùng
`--corpus` và database đánh giá tách biệt đã migration; không dùng dữ liệu nghiên cứu thật để thử.

```bash
cd apps/api &&
export DATABASE_URL="${RESEARCH_EVAL_DATABASE_URL:?Đặt URL database đánh giá tách biệt}" &&
uv run --frozen python -m app.operations research-eval \
  --variant reference --corpus /tmp/research-public-corpus.json --stop-on-provider-error \
  --output /tmp/research-reference.json &&
uv run --frozen python -m app.operations research-eval \
  --variant optimized --corpus /tmp/research-public-corpus.json --stop-on-provider-error \
  --output /tmp/research-optimized.json &&
uv run --frozen python -m app.operations research-eval-compare \
  /tmp/research-reference.json /tmp/research-optimized.json
```

Chỉ chạy biến thể thứ hai sau khi lệnh đầu hoàn tất thành công. `--stop-on-provider-error` dừng
tập câu hỏi sau lượt thất bại do xác thực, hạn mức hoặc sự cố provider. Lệnh vẫn lưu artifact JSON
với mọi lượt đã thử, ghi lý do vào `stopped` và trả mã thoát `2`. Lần đo dừng sớm chỉ dùng để chẩn đoán.

Các lệnh sử dụng model/credential đã cấu hình. Corpus chỉ thay lớp tìm kiếm/tải nguồn bằng tìm
kiếm từ khóa tất định trên cùng tập văn bản; những lời gọi model vẫn thật. Replay không gọi web
và không tự bổ sung URL thiếu. Không suy rộng độ trễ tìm kiếm từ replay sang SearXNG/live web.
Manifest ghi hash corpus chung và pool từng câu hỏi; tập nguồn thực sự được chọn có hash riêng
để quan sát khác biệt do khử trùng/truy hồi.

## Điều kiện kết luận KPI

`research-eval-compare` luôn hiển thị tổng chi phí, nhưng chỉ hiển thị phần trăm thay đổi khi:

- Đủ toàn bộ bộ câu hỏi đã khai báo, không trùng/mất câu hỏi và cả hai lượt đều hoàn tất.
- Cặp `reference` → `optimized` theo đúng cờ pipeline, cùng corpus cố định có checksum.
- Cùng provider/model theo từng câu, cấu hình/effort, prompt và mã nguồn/lockfile.
- Cache lạnh riêng từng lần đánh giá, entailment bật ở cả hai cấu hình.
- Usage đầy đủ; độ phủ trích dẫn/góc nhìn đều 100%, độ phủ thực thể không giảm.

Thiếu điều kiện sẽ hiện `Chưa đủ điều kiện kết luận KPI`; không lấy giao của các lượt thành công
để che lỗi hoặc khẳng định đạt giảm 20% token. Chỉ commit artifact số đo và hash đã kiểm tra,
không commit toàn văn corpus, credential hay dữ liệu kho nội bộ.

Trong JSON của từng câu, `perspectives_covered` liệt kê các mục có trong báo cáo và
`perspectives_with_verified_claims` liệt kê các góc nhìn có nhận định đã qua kiểm chứng.
`writer_fallback_perspectives` ghi các mục máy chủ bổ sung nguyên văn từ nhận định đã kiểm chứng.
Các trường này giúp xác định bước nào thiếu góc nhìn sau khi xóa database thử. Cổng KPI tiếp tục
dùng độ phủ tính trên các mục có thật trong báo cáo.

## Gia cố kiểm chứng 2026-11-20

Lease mỗi bước có UUID riêng; heartbeat, cập nhật cache và kết quả dùng cùng điều kiện ownership
trong giao dịch. Không giữ khóa hàng qua lời gọi model/tìm kiếm/tải trang. Worker cũ mất lease
phải rollback cả kết quả thành công lẫn lỗi, không thay trạng thái/counter/report của worker mới.
Đã thêm migration nullable `8e0a2c4d6f79`; dừng API/worker cũ, nâng schema rồi khởi động bản mới.
Không chạy lẫn worker cũ không có fencing với worker mới. Dữ liệu run hiện có không bị viết lại.

Verifier từ chối cả lô có ID judgement trùng hoặc không thuộc lô. Chỉ cache verdict riêng từng
claim đã qua kiểm tra, TTL24h; bỏ qua cache whole-batch cũ. Phiên bản prompt entailment v3 vô hiệu
hóa cache trước khi có ràng buộc ID duy nhất. Không thay biến thể naive/reference hoặc quality gates.

Fuzzy quote matching giới hạn số phép so sánh token tất định; hết ngân sách trả không khớp.
Exact/normalized matching giữ nguyên. Phần “Khoảng trống bằng chứng” phân biệt thiếu evidence
với có verified claim nhưng writer chưa tổng hợp; không tự thêm section để tăng coverage đo được.
