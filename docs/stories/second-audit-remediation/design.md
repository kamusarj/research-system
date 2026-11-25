# Design

## Authorization and Provenance

Dùng cùng điều kiện sửa research in-review/approved cho mọi đường version/restore/AIaccept.
Quan hệ tác động research đã duyệt chỉ owner. Xóa source phải kiểm tra evidence canonical/applied
bất kể origin document/chat, giữ mã lỗi provenance và audit không có nội dung.

## Research Concurrency and Verification

Lease token/generation phải được kiểm tra trước heartbeat và ghi kết quả; stale worker không được
ghi đè trạng thái/số đo/cache/report. Ưu tiên giữ ranh giới transaction ngắn, không khóa DB qua LLM.
Migration token nếu cần là nullable additive và tương thích database cũ.
Từ chối judgement trùng/mâu thuẫn trước khi áp dụng/cache; cùng TTL24h ở mọi cache entailment.
Gaps báo cáo dựa trên evidence thực tế; không thêm facts chưa verified. Fuzzy search có computation
budget tất định và fail closed khi hết, vẫn giữ exact/normalized matching.

## Operations and Search

Restore có preflight checksum/format, transaction/error-stop và chỉ resume khi đã kiểm chứng; chỉ
thực thi trong test với Docker giả hoặc tài nguyên tách biệt, không restore dữ liệu thật.
Hybrid áp dụng cùng bộ lọc cho kết quả fusion và phân trang; secret task API/worker đồng bộ.
Limiter xóa identity hết hạn và giữ đúng cửa sổ/race protection, không nới giới hạn truy cập.
