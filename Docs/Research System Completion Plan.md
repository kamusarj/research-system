# Kế hoạch hoàn thiện Hệ thống nghiên cứu

## Mục tiêu

Hoàn thiện Hệ thống nghiên cứu thành lõi vận hành độc lập trước khi xây bot Discord. Về sau,
Discord chỉ gửi URL và siêu dữ liệu nguồn vào hợp đồng tiếp nhận công khai; toàn bộ việc tải,
trích xuất, phân loại, khử trùng lặp, kiểm duyệt, xuất bản, tìm kiếm và tạo bản chiếu đồ thị
thuộc trách nhiệm của Hệ thống nghiên cứu.

```text
Liên kết từ Discord / nhập thủ công / API
        -> tiếp nhận URL
        -> tải an toàn + trích xuất
        -> khử trùng lặp
        -> AI phân loại theo cấu trúc
        -> chính sách ngưỡng / hàng chờ kiểm duyệt
        -> ResearchItem đã duyệt
        -> bản chiếu tìm kiếm + đồ thị
```

## Quyết định kiến trúc

1. PostgreSQL vẫn là nguồn dữ liệu chuẩn. Neo4j và các công cụ tìm kiếm là bản chiếu có thể tạo lại.
2. Luồng tiếp nhận không phụ thuộc loại nguồn. `source_type=discord` chỉ là siêu dữ liệu, không phải
   logic nghiệp vụ dành riêng cho Discord.
3. Mỗi nhà cung cấp mô hình triển khai cùng một hợp đồng đầu ra có cấu trúc và được kiểm tra bằng Pydantic.
4. Khóa của nhà cung cấp chỉ lấy từ biến môi trường hoặc trình quản lý bí mật và không bao giờ được API trả về.
5. AI không được tự xuất bản nội dung có độ tin cậy thấp khi chưa có người kiểm duyệt.
6. Nút đồ thị dùng khóa ổn định có kiểu; thao tác ghi bản chiếu phải có tính lũy đẳng.
7. Tiếng Việt là ngôn ngữ duy nhất của giao diện; nội dung nghiên cứu vẫn giữ ngôn ngữ gốc để bảo
   toàn ý nghĩa và nguồn gốc. Quy tắc này được chốt tại quyết định 0044/DEC-057.

## Chiến lược nhà cung cấp

| Nhà cung cấp | Cách kết nối | Cách nhận đầu ra có cấu trúc |
|---|---|---|
| Ollama | `/api/generate` | Định dạng JSON, kiểm tra tại máy cục bộ |
| OpenAI | Responses API | JSON Schema qua `text.format` |
| DeepSeek | Chat Completions tương thích OpenAI | Đối tượng JSON + kiểm tra prompt/schema |
| Google Gemini | `generateContent` | Kiểu MIME JSON + schema phản hồi |
| OpenRouter | Chat Completions tương thích OpenAI | `response_format=json_schema` |
| Mistral | `/v1/chat/completions` | `response_format=json_schema` + kiểm tra Pydantic cục bộ |

Tên mô hình của nhà cung cấp là cấu hình, không phải quy tắc nghiệp vụ viết cứng. Khi lời gọi nhà
cung cấp thất bại, mục tiếp nhận vẫn được giữ cùng lỗi có hướng xử lý và có thể thử lại.

## Hệ phân loại của Đồ thị tri thức v1

Các loại nút:

- `ResearchItem`
- `Concept`
- `Technology`
- `AgentPattern`
- `BusinessDomain`
- `Person`
- `CollectorSource`
- `ResearchGap`

Các loại cạnh:

- `RESEARCHES`, `USES_TECH`, `IMPLEMENTS_PATTERN`, `APPLIES_TO`, `AUTHORED_BY`
- `COLLECTED_FROM`, `REFERENCES`, `EXTENDS`, `SUPPORTS`, `CONTRADICTS`
- `FILLS_GAP`, `SYNTHESIZED_INTO`

Bản chiếu PostgreSQL được phát hành trước. Bộ chuyển đổi Neo4j tùy chọn hiện tạo lại cả chế độ
quan hệ lẫn phân cấp bằng ràng buộc duy nhất kết hợp, `MERGE` có tham số và `UNWIND` theo lô;
Neo4j không bao giờ trở thành đường ghi dữ liệu chuẩn. Tính tương đương khi tạo lại, khả năng lặp,
việc dọn dữ liệu cũ, giới hạn đọc và lỗi nhà cung cấp rõ ràng đều có kiểm thử tự động cùng bằng
chứng từ máy chủ dùng một lần.

## Yêu cầu giao diện

- Canvas Cytoscape.js có thể tương tác, hỗ trợ kéo, thu phóng, vừa khung, nhiều bố cục và chọn phần tử.
- Chú giải loại nút/cạnh, tìm kiếm, bộ lọc, chỉ số bậc/độ phủ và bảng chi tiết.
- Có thể mở chi tiết nghiên cứu từ `ResearchItem`; đồ thị lân cận và đường đi ngắn nhất vẫn do API cung cấp.
- Khung ứng dụng thích ứng màn hình, độ tương phản và trạng thái focus dễ tiếp cận, cùng trạng thái
  đang tải/trống/lỗi có ý nghĩa.
- Giao diện tiếng Việt nhất quán trên toàn ứng dụng, không có bộ chuyển ngôn ngữ.

## Điều kiện bàn giao

### Điều kiện A - Nền tảng tiếp nhận và nhà cung cấp

- API gửi URL và giao diện hộp thư nguồn.
- Tải HTTP(S) an toàn trước SSRF, trích xuất văn bản sạch và khử trùng lặp bằng dấu vân tay nội dung.
- Phân loại có cấu trúc, theo dõi nguồn gốc, trạng thái có thể thử lại và thao tác duyệt/từ chối rõ ràng.
- Danh mục Ollama/OpenAI/DeepSeek/Gemini/OpenRouter/Mistral có điểm cuối trạng thái cấu hình và
  không dùng phương án giả lập âm thầm trong tiến trình.

### Điều kiện B - Đồ thị tri thức và trải nghiệm tiếng Việt

- Bản chiếu hệ phân loại có kiểu từ các kết quả phân loại đã chấp nhận.
- Trực quan hóa mạng có tương tác cùng thống kê và bộ lọc đồ thị.
- Khung ứng dụng và các quy trình chính dùng tiếng Việt.

### Điều kiện C - Hoàn thiện vận hành

- Xác thực/RBAC, triển khai bí mật đã mã hóa, tệp đính kèm nhị phân trên MinIO và hàng đợi tác vụ nền.
- Chính sách thử lại/thư lỗi, giới hạn tần suất, khả năng quan sát, sao lưu/khôi phục và kiểm thử tích hợp/E2E.
- Bộ chuyển đổi Meilisearch/pgvector/Neo4j được xác minh là các bản chiếu có thể tạo lại.

Nền tảng hiện tại: luồng tiếp nhận URL dùng hàng đợi tác vụ dựa trên PostgreSQL với lease cho worker,
giới hạn số lần thử lại theo yêu cầu/tác vụ và thao tác thử lại rõ ràng trên từng dòng. Các bộ chuyển
đổi nguồn hỗ trợ kho mã, tệp, issue và pull request GitHub; siêu dữ liệu công khai và Reel Facebook;
bài báo từ arXiv/DOI/nhà xuất bản; lớp văn bản PDF trực tiếp; cùng bài viết phổ thông. Tra cứu DOI dùng
Crossref trước, rồi thương lượng nội dung CSL không phụ thuộc registry khi DOI hợp lệ được đăng ký ở nơi khác.
Kết quả trích xuất một phần và lỗi có kiểu vẫn có thể kiểm duyệt mà không làm worker dừng đột ngột.
Ranh giới tệp đính kèm hỗ trợ thao tác ghi MinIO/S3-compatible có thể hoàn tác và đọc cục bộ cũ theo
scheme. Công cụ dòng lệnh ưu tiên chạy thử hiện có thể kiểm kê, sao chép-xác minh, cập nhật tham chiếu
theo giao dịch và xác minh lại mà không xóa byte cục bộ; kế hoạch trên môi trường chính báo cáo ba đối
tượng hợp lệ, sạch. Việc cấp bucket được quản lý và thao tác/loại bỏ dữ liệu production có thẩm quyền
vẫn là công việc vận hành. Xác thực Argon2 cục bộ, phiên cookie opaque, CSRF, RBAC theo vai trò chủ sở
hữu/nhà nghiên cứu/người xem, ghi nhận người thao tác, cấu hình production đóng khi lỗi và hỗ trợ bí
mật gắn qua tệp trong Compose đã được triển khai; OIDC/MFA bên ngoài, kết thúc TLS và xoay vòng bí mật
vẫn thuộc khâu triển khai. OCR Tesseract có giới hạn cho PDF quét từ URL/tải lên, phương án Browserless
cho bài viết công khai chỉ chạy JavaScript và xử lý lại Reel/video bằng bản chép lời do người dùng cung
cấp đều đã được triển khai với giới hạn có kiểu, nguồn gốc, rào chắn SSRF/tài nguyên và kiểm duyệt bởi
con người. Kết nối Redis và bộ thu thập theo lịch vẫn còn mở. Mã tương quan yêu cầu an toàn cho production,
nhật ký JSON cho API/worker và điểm cuối số liệu API có xác thực, nhãn bị giới hạn đã được triển khai;
việc cấp scraper, thời gian lưu, cảnh báo và tổng hợp nhiều replica ở tầng triển khai vẫn là công việc
vận hành. Bản chiếu Neo4j Community tùy chọn được triển khai sau hợp đồng kho đồ thị hiện có và đã xác
minh bằng máy chủ thật dùng một lần, không mở cổng host. Meilisearch hiện tạo lại nghiên cứu đã duyệt
qua chỉ mục trung gian đã kiểm tra và đổi chỉ mục nguyên tử; tìm kiếm ngữ nghĩa dùng embedding Mistral
thật trong bản chiếu pgvector `vector(1024)` riêng với chỉ mục cosine HNSW. Cả hai đã được xác minh bằng
việc tạo lại nhiều lần, dọn dòng cũ có kiểm soát, đối chiếu dữ liệu chuẩn và đường đọc thật. Điều kiện C
chỉ còn mở cho các việc do khâu triển khai sở hữu như di chuyển/sao lưu MinIO production có thẩm quyền,
TLS/egress, xoay vòng bí mật bên ngoài và chính sách lưu/cảnh báo telemetry.

### Điều kiện D - Bộ kết nối Discord

- Hợp đồng lần xuất hiện/mục không phụ thuộc loại nguồn được chấp nhận trong
  `Docs/Intake Occurrence and Receipt Specification.md`. Schema bổ sung, API, cơ chế ghi kép cho dữ
  liệu cũ, đường dẫn tài liệu bền vững và xác thực tài khoản dịch vụ theo namespace đã được triển khai
  và xác minh cục bộ. Phần này hoàn tất điều kiện phía ứng dụng nhưng chưa khởi chạy bot; vẫn cần chủ
  sản phẩm chấp nhận Graph v2 và chốt chính sách vận hành ở tầng triển khai.
- Bot dùng danh sách kênh/guild được phép, xác thực người gửi và tự động gửi URL từ tin nhắn thông thường
  vào API tiếp nhận; `/submit` chỉ là tùy chọn tương thích, không phải quy trình chính.
- Một tin nhắn Discord tương ứng một biên nhận; mỗi URL đã chuẩn hóa hoặc PDF đã lưu tương ứng một mục
  biên nhận. Thử lại cùng ID tin nhắn + URL chuẩn hóa có tính lũy đẳng; cùng URL trong tin nhắn khác vẫn
  giữ một lần xuất hiện mới mà không nhân đôi quá trình xử lý URL.
- Bot báo trạng thái đã nhận/trùng lặp/cần duyệt/thất bại mà không sở hữu logic trích xuất hay đồ thị.
- Bot cung cấp các lệnh `/help`, `/guide`, `/sources`, `/ping`, `/pin`, `/submit` và `/status` sau khi
  kiểm tra danh sách cho phép; đồng bộ chúng vào từng guild đã cấu hình và quảng bá `/help` trong trạng
  thái hoạt động. `/pin` chỉ tác động đến tin nhắn cùng kênh và yêu cầu quyền Discord `PIN_MESSAGES` cho
  cả người gọi lẫn bot; quyền này không bổ sung thẩm quyền trên Research API.
- Mở rộng ngày 2026-07-30: mục URL từ Discord mặc định yêu cầu đường tự duyệt có rào chắn hiện có.
  Nguồn hoàn chỉnh, độ tin cậy cao trở thành nghiên cứu đã duyệt và đi vào đồ thị quan hệ; vị trí trong
  hệ phân cấp chuẩn vẫn là bộ thay đổi cần kiểm soát. Khi duyệt, bộ phát hiện độ phủ thấp được làm mới;
  thao tác đọc biên nhận theo namespace chỉ trả về khoảng trống đang hoạt động liên quan đến mục đó để
  bot có thể thông báo bằng tiếng Việt trong đúng kênh ban đầu. Reel chưa có bản chép lời và nguồn có độ
  tin cậy thấp vẫn cần kiểm duyệt.
- Hướng dẫn thiết lập, thông tin xác thực tối thiểu, các ca nghiệm thu trực tiếp, bằng chứng đồ thị/khoảng
  trống và dọn dẹp được mô tả trong `Docs/Discord Bot Test Runbook.md`.

## Tài liệu tham khảo bên ngoài

- Đầu ra có cấu trúc của OpenAI: <https://developers.openai.com/api/docs/guides/structured-outputs>
- Đầu ra JSON của DeepSeek: <https://api-docs.deepseek.com/guides/json_mode/>
- Đầu ra có cấu trúc của Gemini: <https://ai.google.dev/gemini-api/docs/structured-output>
- Đầu ra có cấu trúc của OpenRouter: <https://openrouter.ai/docs/guides/features/structured-outputs>
- Đầu ra có cấu trúc của Mistral: <https://docs.mistral.ai/studio-api/conversations/structured-output/custom>
- `MERGE` trong Neo4j: <https://neo4j.com/docs/cypher-manual/current/clauses/merge/>
- Hiệu năng Neo4j Python: <https://neo4j.com/docs/python-manual/current/performance/>
- Cytoscape.js: <https://js.cytoscape.org/>
- Phương án i18n cho Next.js đã cân nhắc: <https://next-intl.dev/>
