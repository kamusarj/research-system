# Quy ước ngôn ngữ tiếng Việt

Tài liệu này thống nhất cách viết cho giao diện, thông báo, bot Discord và tài liệu hướng dẫn của dự án.

## Mục tiêu

- Dùng tiếng Việt tự nhiên, rõ ý và phù hợp với người đang nghiên cứu hệ thống AI.
- Không viết quá hàn lâm khi một cách nói thông dụng đã đủ chính xác.
- Không giản lược đến mức làm mất nghĩa kỹ thuật hoặc khó tra cứu tài liệu gốc.
- Một khái niệm nên có một cách gọi chính, dùng nhất quán trên mọi bề mặt sản phẩm.

## Giọng văn

Ưu tiên câu chủ động, ngắn vừa phải và nói rõ người dùng cần làm gì. Ví dụ:

- Nên viết: “Không thể tải nguồn. Hãy kiểm tra liên kết rồi thử lại.”
- Tránh viết: “Quá trình thu nạp tài nguyên đã gặp ngoại lệ.”
- Tránh viết: “Lỗi link.”

Thông báo lỗi cần gồm phần giải thích dễ hiểu. Mã lỗi như `INVALID_URL` hoặc trạng thái như `partial_success` vẫn được giữ để người vận hành tra cứu.

## Thuật ngữ thống nhất

| Thuật ngữ gốc | Cách dùng trong sản phẩm |
| --- | --- |
| workspace | không gian / không gian nghiên cứu |
| pipeline | quy trình xử lý |
| job | tác vụ |
| metadata | siêu dữ liệu |
| knowledge graph | đồ thị tri thức |
| graph | đồ thị |
| ontology | hệ phân loại tri thức / cấu trúc tri thức |
| node / edge | nút / cạnh |
| chat | trò chuyện / cuộc trò chuyện |
| brainstorm | trao đổi hoặc phát triển ý tưởng |
| snapshot | bản chụp |
| provider | nhà cung cấp |
| workflow | quy trình |
| governance | kiểm soát / quản trị |
| publish | xuất bản |
| source | nguồn |
| editor | trình soạn thảo |
| preview | bản xem trước |
| raw | nguyên bản |
| paper-fit | mức phù hợp nghiên cứu |
| hard gate | điều kiện bắt buộc |
| change set | bộ thay đổi |
| draft | bản nháp |
| patch | bản sửa |
| upload | tải lên |
| streaming | tải hoặc truyền theo luồng |
| claim | luận điểm |
| feed | nguồn tin |
| cache | bộ nhớ tạm |
| transcript | bản chép lời |
| timestamp | mốc thời gian |
| AI agent | tác nhân AI |

## Nội dung giữ nguyên

Không dịch tên riêng và định danh cần dùng để cấu hình hoặc tra cứu, gồm:

- Tên sản phẩm, nhà cung cấp và công nghệ: ChatGPT, OpenAI, DeepSeek, Mistral, GitHub, PostgreSQL, pgvector, Meilisearch, Neo4j, MinIO, Ollama.
- Định dạng và giao thức: Markdown, PDF, DOCX, LaTeX, RSS, API, HTTP, MIME, UTF-8, RAG.
- Đường dẫn API, biến môi trường, tên lệnh, tên tệp, khóa JSON, mã trạng thái và mã lỗi.
- Tiêu đề, trích dẫn, nội dung tài liệu và dữ liệu do người dùng hoặc nguồn bên ngoài cung cấp.

Khi một thuật ngữ tiếng Anh cần thiết để tra cứu, hãy viết tiếng Việt trước và có thể thêm thuật ngữ gốc trong ngoặc ở lần xuất hiện đầu tiên.

## Phạm vi tiếng Việt hoàn toàn

Web và bot Discord chỉ hiển thị tiếng Việt. Không có bộ chuyển ngôn ngữ trong giao diện. Các bản ghi lịch sử trong `AI_LOGS/`, migration cũ và dữ liệu nguồn không được dịch lại vì việc đó có thể làm sai dấu vết kiểm toán hoặc nội dung gốc.
