# Kế hoạch triển khai Hệ thống nghiên cứu

> Quy ước hiện hành: giao diện, thông báo API và bot Discord chỉ dùng tiếng Việt theo
> `Docs/Quy uoc ngon ngu tieng Viet.md`. Tên công nghệ, định danh kỹ thuật và nội dung nguồn gốc
> vẫn giữ nguyên để dễ tra cứu và không làm sai dữ liệu nghiên cứu.

> Kế hoạch triển khai Hệ thống nghiên cứu dựa trên:
>
> - `Docs/Research System Brainstorm.md`
> - `Docs/Research System Architecture Design.md`
>
> **Trạng thái:** Giai đoạn 0-6 đã hoàn tất; Giai đoạn 7 đang thực hiện
> **Mục tiêu hiện tại:** MVP phân tích khoảng trống sau khi kho tri thức, tìm kiếm và đồ thị nghiên cứu đã được kiểm chứng
> **Phạm vi ưu tiên:** Ưu tiên chạy cục bộ, nghiên cứu sâu do con người phê duyệt
>
> Cập nhật 2026-07-13: phần triển khai hiện nằm trong `apps/api` và `apps/web`. Giai đoạn 7 đã có
> bộ phát hiện đồ thị độ phủ thấp, không gian khoảng trống, thao tác giao/ưu tiên/bỏ qua/tạm hoãn,
> tạo bản nháp nghiên cứu sâu và điều kiện phê duyệt bởi con người. Tín hiệu xu hướng/tìm kiếm thất
> bại và bản tin tuần vẫn để bước sau.
>
> Cập nhật 2026-07-30: cổng kết nối Discord đã dùng cơ chế tự duyệt có rào chắn cho URL đủ độ tin cậy;
> mỗi liên kết được duyệt sẽ làm mới các khoảng trống độ phủ thấp, biên nhận trả về khoảng trống đang
> hoạt động có liên quan và bot thông báo ngay trong kênh. Bot không có quyền duyệt bộ thay đổi đồ thị;
> Reel thiếu bản chép lời và nguồn chỉ thành công một phần hoặc có độ tin cậy thấp vẫn vào hàng chờ duyệt.
>
> Cập nhật 2026-08-01: `/chat` hỗ trợ nhập một lần liên kết chia sẻ ChatGPT công khai thành bản chụp
> cục bộ có thông tin nguồn gốc. Chỉ nội dung người dùng/trợ lý hiển thị được nhập; trò chuyện tiếp dùng nhà cung cấp
> hiện có và không đồng bộ hoặc ghi ngược lên ChatGPT.
>
> Kế hoạch hoàn thiện hệ thống trước khi tích hợp Discord được chốt tại
> `Docs/Research System Completion Plan.md`.

> Cập nhật 2026-09-05: `/chat` cho phép researcher/owner dùng API key OpenAI/DeepSeek riêng,
> giữ tạm trong trang và request server. Chỉ nguồn khóa `system|personal`, provider và model
> được lưu cùng cuộc trò chuyện; khóa không lưu bền vững. Phiên cá nhân thiếu khóa không
> dùng khóa hệ thống. Bổ sung cùng ngày: tải model bằng khóa, chọn từ danh sách và
> chủ động kiểm tra trước khi UI lưu kết nối. Probe tối đa 16 output token, có thông
> báo khả năng có phí; không có dữ liệu nghiên cứu. Phân biệt lỗi key/credit/quota,
> quyền/model, tốc độ/mạng cả khi kết nối lẫn chat; không suy số dư từ model list.
> Xem `docs/decisions/0046-ephemeral-personal-chat-api.md` và
> `docs/decisions/0047-personal-chat-model-validation.md`.

> Cập nhật 2026-11-03: runtime cục bộ đã bật owner/auth và nghiên cứu bounded có trích dẫn;
> API/worker không đặc quyền, cầu nối CLI được cô lập, backup tự động có kiểm tra restore.
> Chat đã tối ưu tải ban đầu/lịch sử; verifier giữ đầy đủ bằng chứng khi gộp và cache.
> Chưa có tên miền nhóm; nghiệm thu sản phẩm, credential bên ngoài và KPI chi phí toàn pipeline
> vẫn là các mục riêng. Trạng thái hiện tại ở `AI_LOGS/HANDOFF.md`, lịch sử ở session logs.

---

## 1. Mục tiêu triển khai

Triển khai Hệ thống nghiên cứu theo từng bước, bắt đầu từ một MVP chạy cục bộ để nhóm quản lý nghiên cứu về **Tác nhân AI cho doanh nghiệp**.

MVP cần giải quyết trước:

- Lưu trữ nghiên cứu tập trung.
- Tạo, sửa và duyệt nghiên cứu bằng Markdown.
- Tìm kiếm toàn văn và tìm kiếm ngữ nghĩa cơ bản.
- Trực quan hóa Đồ thị tri thức cơ bản.
- AI hỗ trợ tóm tắt, gắn thẻ và trích xuất khái niệm.
- Có nền móng cho bộ thu thập tự động, nhưng chưa cần tự động hóa hoàn toàn ngay.

Không làm ngay trong MVP:

- Trình thu thập nhiều loại nguồn phức tạp.
- Tác nhân nghiên cứu sâu tự động hoàn chỉnh.
- SSO/Keycloak cho môi trường production.
- Triển khai Kubernetes hoặc đám mây.

---

## 2. Chiến lược triển khai

### 2.1. Cách tiếp cận

Triển khai theo hướng **ưu tiên cục bộ, mô-đun hóa, dễ nâng cấp**:

1. Dựng nhanh một bản chạy được trên máy cục bộ.
2. Giữ API và mô hình dữ liệu gần với kiến trúc cuối.
3. Tách rõ miền nghiệp vụ lõi, quy trình worker và tầng bản chiếu.
4. Cho phép thay thành phần gọn nhẹ bằng thành phần đầy đủ sau này.

### 2.2. Kiến trúc mục tiêu

Kiến trúc cuối vẫn theo tài liệu thiết kế:

- Giao diện: Next.js.
- Phần máy chủ: FastAPI.
- Cơ sở dữ liệu chính: PostgreSQL + pgvector.
- Đồ thị: Neo4j.
- Tìm kiếm: Meilisearch.
- Hàng đợi/bộ nhớ đệm: Redis.
- Lưu trữ tệp: MinIO.
- Mô hình ngôn ngữ cục bộ: Ollama.
- Tiến trình nền: Celery/RQ hoặc tương đương.

### 2.3. Kiến trúc MVP cục bộ

Để tránh xây quá mức cần thiết, MVP cục bộ có thể bắt đầu bằng:

- Phần máy chủ FastAPI.
- SQLite hoặc PostgreSQL cục bộ.
- Giao diện tĩnh hoặc Next.js tùy thời gian.
- Tìm kiếm đơn giản trước, Meilisearch ở giai đoạn sau.
- Bản chiếu API đồ thị đơn giản trước, Neo4j ở giai đoạn sau.
- Bộ chuyển đổi Ollama/nhà cung cấp đám mây để AI làm giàu dữ liệu; ứng dụng không có nhà cung cấp giả.

Quy tắc: dù ban đầu dùng phần máy chủ gọn nhẹ, đường dẫn API và schema phải thiết kế theo `/api/v1` để không làm hỏng giao diện khi nâng cấp.

---

## 3. Phạm vi chức năng theo giai đoạn

## Giai đoạn 0 - Đặc tả sản phẩm và kỹ thuật

Mục tiêu: chuyển phần trao đổi ý tưởng thành bộ đặc tả đủ rõ để triển khai.

Sản phẩm bàn giao:

- Đặc tả sản phẩm cho MVP.
- Hợp đồng API.
- Schema cơ sở dữ liệu v1.
- Luồng giao diện và khung màn hình sát thực tế hơn.
- Hướng dẫn triển khai cục bộ.
- Danh sách tiêu chí nghiệm thu.
- Định dạng nhật ký bàn giao AI để nhiều tác nhân AI có thể luân phiên tiếp quản công việc.

Nội dung cần chốt:

- Vòng đời mục nghiên cứu.
- Siêu dữ liệu bắt buộc.
- Quyền theo vai trò.
- Cách hoạt động của tìm kiếm và bộ lọc.
- Các loại nút/cạnh đồ thị trong MVP.
- Trường nào do AI tự tạo, trường nào con người có thể sửa.
- Quy ước ghi nhật ký khi đổi tác nhân hoặc hết hạn mức.

Tiêu chí nghiệm thu:

- Một kỹ sư đọc tài liệu có thể bắt đầu triển khai mà không cần hỏi lại các quyết định lớn.
- Một tác nhân AI mới có thể đọc nhật ký bàn giao trong 5 phút và biết ngay trạng thái hiện tại,
  việc đang làm và phần không được thay đổi.

---

## Giai đoạn 1 - Nền tảng cục bộ

Mục tiêu: tạo bộ khung ứng dụng chạy cục bộ.

Phần máy chủ:

- Ứng dụng FastAPI.
- `/api/v1/health`.
- Cấu hình bằng `.env`.
- Kết nối cơ sở dữ liệu.
- Cơ chế migration.
- Định dạng lỗi cơ bản.
- CORS cho giao diện cục bộ.

Giao diện:

- Khung ứng dụng.
- Thanh bên/điều hướng.
- Màn hình tổng quan tạm.
- Trình khách API.

Hạ tầng:

- Docker Compose cục bộ.
- Dịch vụ tối thiểu: API, giao diện, cơ sở dữ liệu.
- Dịch vụ tùy chọn bổ sung sau: Redis, Meilisearch, Neo4j, MinIO, Ollama.

Tiêu chí nghiệm thu:

- Chạy được ứng dụng cục bộ bằng một lệnh.
- Kiểm tra sức khỏe đạt.
- Giao diện gọi được phần máy chủ.

---

## Giai đoạn 2 - Lõi kho tri thức nghiên cứu

Mục tiêu: quản lý mục nghiên cứu thủ công.

Chức năng phần máy chủ:

- Tạo mục nghiên cứu.
- Liệt kê mục nghiên cứu kèm bộ lọc.
- Xem chi tiết.
- Cập nhật.
- Lưu trữ hoặc xóa mềm.
- Gửi kiểm duyệt.
- Phê duyệt.
- Lịch sử phiên bản.
- Bình luận cơ bản.
- Thẻ.
- Quan hệ thủ công.

Các trường của mục nghiên cứu:

- `id`
- `display_id`
- `title`
- `type`
- `status`
- `collection_method`
- `summary`
- `content`
- `source_url`
- `authors`
- `tags`
- `created_at`
- `updated_at`
- `approved_at`
- `metadata`

Chức năng giao diện:

- Danh sách nghiên cứu.
- Chi tiết nghiên cứu.
- Trình soạn thảo Markdown.
- Không gian soạn tài liệu cho các định dạng nguồn UTF-8 có thể chỉnh sửa.
- Bộ nhớ đệm bản nháp cục bộ theo người dùng, ghi ngay mọi chỉnh sửa, tồn tại sau khi tải lại/khởi
  động lại trình duyệt, không có thao tác bỏ thủ công và chỉ xóa sau khi tạo bản có kiểm soát thành công.
- Trình soạn `Nội dung tài liệu` thống nhất: nhập trực tiếp hoặc nạp Markdown/TXT/LaTeX/
  reStructuredText/AsciiDoc/HTML cục bộ trước khi tạo; các định dạng UTF-8 này vẫn sửa được sau khi
  tải lên với chế độ Nguyên bản, Xem trước và Song song.
- Tệp PDF/DOCX đã trích xuất thành công cũng mở trong cùng trình soạn thảo dưới dạng văn bản dẫn xuất
  AI có thể đọc và được ghi nhãn rõ. Tệp nhị phân đã tải lên luôn bất biến, có thể xem/tải riêng;
  thao tác Lưu tạo phiên bản dẫn xuất UTF-8 rồi chạy lại quy trình xử lý/RAG hiện có, không giả vờ
  giữ nguyên bố cục PDF/Office qua một vòng chuyển đổi.
- Khung trao đổi tài liệu theo ngữ cảnh nằm cạnh nguồn mới hoặc đã tải lên. Mỗi lần bấm Gửi nhận
  nguồn hiện tại đã giới hạn/che dữ liệu nhạy cảm cùng lịch sử gần đây; phản hồi chỉ đổi văn bản cục
  bộ sau thao tác rõ ràng như Thay đoạn đã chọn, Chèn tại con trỏ hoặc Nối cuối tài liệu. Lỗi nhà cung
  cấp có thể thử lại dùng phản hồi an toàn đã dịch và giữ một thao tác Thử lại do người dùng chủ động,
  không nhân đôi câu hỏi hiển thị hoặc tự lặp lời gọi tính phí. Mệnh lệnh sửa bằng tiếng Việt được
  chuyển vào quy trình sửa tức thời có cấu trúc thay vì trả về lời khuyên; chúng nhắm tới đoạn đang
  chọn hoặc toàn bộ nguồn có giới hạn và luôn yêu cầu Chấp nhận/Từ chối. Khi đích là tài liệu LaTeX
  hoàn chỉnh, đầu ra của nhà cung cấp cũng phải là tài liệu LaTeX hoàn chỉnh; Markdown giải thích,
  đoạn mã có hàng rào hoặc lời bình cuối sẽ bị từ chối an toàn trước khi duyệt và không thể thay nguồn
  nguyên bản. Giá trị nhạy cảm dùng token tạm thời duy nhất chỉ gửi tới nhà cung cấp rồi được khôi phục
  cục bộ trước khi duyệt bản sửa; marker che dữ liệu bị thiếu, đổi hoặc rò rỉ đều bị từ chối an toàn và
  không bao giờ đi vào nguồn nguyên bản.
- Bản sửa AI có cấu trúc dựa trên đoạn chọn, gắn với đúng phiên bản và vùng nguồn cục bộ. Mọi kết
  quả thay đổi đều hiển thị đầy đủ phần gốc/phần thay thế và yêu cầu Chấp nhận hoặc Từ chối trước khi
  đổi bản nháp trong bộ nhớ đệm; đầu ra giống hệt chỉ được báo là không thay đổi. Chỉ thao tác Tạo/Lưu
  mới quản lý lịch sử nguồn bất biến.
- Yêu cầu AI trên tài liệu giữ lỗi có kiểu qua ngân sách proxy trình duyệt giới hạn 180 giây, đủ bao
  phủ thời gian DeepSeek thành công 131,1 giây đã quan sát; lỗi tạm thời cung cấp thao tác thử lại do
  người dùng chủ động. Chế độ soạn mặc định vẫn ưu tiên trình soạn thảo, phần kiểm tra an toàn Nguyên
  bản/Xem trước/Song song được thu gọn đến khi cần.
- Tự động làm mới RAG tài liệu theo phiên bản cho cuộc trò chuyện có phạm vi, kèm trạng thái thử lại rõ ràng.
- Thao tác theo đoạn văn bản đã chọn: thao tác tài liệu áp dụng bản sửa cục bộ có kiểu, an toàn trước
  xung đột; thao tác trò chuyện chỉ chuẩn bị bản nháp có trích dẫn và vẫn yêu cầu bấm Gửi.
- Bảng siêu dữ liệu.
- Nhãn trạng thái.
- Trình sửa thẻ.
- Khu vực quan hệ.

Tiêu chí nghiệm thu:

- Người dùng tạo bản nháp nghiên cứu.
- Người dùng có thể soạn tài liệu nguồn trực tiếp, F5 vẫn khôi phục bản nháp và tạo tài liệu qua
  cùng quy trình tải lên/kiểm duyệt hiện có.
- Người dùng có thể nhập nguồn UTF-8 vào `Nội dung tài liệu` để sửa trước khi tạo; các nguồn Markdown,
  TXT, LaTeX, reStructuredText, AsciiDoc và HTML đã tải lên tiếp tục sửa được theo phiên bản.
- Người dùng có thể trò chuyện với AI ngay cạnh nội dung hiện tại để phát triển ý tưởng; Gửi và áp
  dụng câu trả lời là hai hành động riêng. Nếu nhà cung cấp hết thời gian chờ, câu hỏi vẫn được giữ và
  người dùng có thể chủ động thử lại mà không tạo lượt trò chuyện trùng. Lệnh sửa trực tiếp trong ô
  trò chuyện phải tạo bản so sánh đầy đủ phần cũ/mới thay vì trả lời hướng dẫn. Chọn đoạn để AI viết
  lại luôn hiển thị đầy đủ phần cũ/mới và chỉ sửa bản nháp cục bộ sau khi người dùng Chấp nhận; Từ chối
  giữ nguyên nguồn, còn đầu ra giống hệt mới báo không thay đổi. Chỉ Tạo/Lưu/Khôi phục mới tạo phiên
  bản bền vững và tự lập lại RAG cho tài liệu.
- Người dùng có thể bôi đen một đoạn trong phần Trao đổi ý tưởng để Hỏi AI, Giải thích hoặc Tóm tắt;
  thao tác chỉ điền ô soạn và không tự gửi hoặc sửa lịch sử trò chuyện.
- Người dùng gửi kiểm duyệt.
- Chủ sở hữu/nhà nghiên cứu phê duyệt.
- Mục đã duyệt hiển thị trong thư viện.
- Chỉnh sửa tạo bản chụp phiên bản.

---

## Giai đoạn 3 - Tìm kiếm và khám phá

Mục tiêu: tìm kiếm nghiên cứu hiệu quả.

Phần máy chủ:

- Tìm kiếm toàn văn.
- Lọc theo trạng thái, loại, thẻ, cách thu thập và ngày.
- API nghiên cứu liên quan ban đầu dựa trên thẻ/quan hệ.
- Tìm kiếm ngữ nghĩa nếu pgvector/embedding đã sẵn sàng.

Giao diện:

- Trang tìm kiếm.
- Thanh tìm kiếm toàn cục.
- Bộ lọc.
- Thẻ kết quả.
- Nghiên cứu liên quan trên trang chi tiết.

Lộ trình triển khai:

1. Tìm kiếm từ vựng trong cơ sở dữ liệu là mặc định cục bộ và đường tương thích. **Hoàn thành.**
2. Bản chiếu Meilisearch chỉ chứa dữ liệu đã duyệt, dùng chỉ mục trung gian/đổi nguyên tử và chủ sở
   hữu chủ động tạo lại. **Hoàn thành, đã chứng minh bằng máy chủ thật.**
3. Các đoạn embedding Mistral trong pgvector `vector(1024)` + tìm kiếm ngữ nghĩa cosine HNSW.
   **Hoàn thành, đã chứng minh trên PostgreSQL đang chạy.**

Tiêu chí nghiệm thu:

- Tìm kiếm theo tiêu đề, nội dung và thẻ hoạt động.
- Bộ lọc không làm mất phân trang.
- Mục mới đã duyệt có thể tìm thấy sau khi lưu.

---

## Giai đoạn 4 - MVP Đồ thị tri thức

Mục tiêu: có trực quan hóa đồ thị cơ bản.

Các loại nút trong MVP:

- ResearchItem.
- Concept.
- Technology.
- Person.
- BusinessDomain.
- CollectorSource.

Các loại cạnh trong MVP:

- RESEARCHES.
- USES_TECH.
- AUTHORED_BY.
- APPLIES_TO.
- REFERENCES.
- EXTENDS.
- SUPPORTS.
- CONTRADICTS.

Phần máy chủ:

- Tạo bản chiếu đồ thị từ mục nghiên cứu, thẻ và quan hệ.
- `/api/v1/graph`.
- `/api/v1/graph/node/{id}`.
- `/api/v1/graph/ego/{id}`.
- `/api/v1/graph/path`.

Giao diện:

- Trình xem đồ thị.
- Bộ lọc nút.
- Bấm nút để xem chi tiết.
- Đồ thị lân cận.
- Chú giải.
- Chế độ quan hệ và phân cấp dùng cùng tập nút đã duyệt; chế độ phân cấp được chiếu lại từ các quan hệ
  mang ý nghĩa thành viên/vị trí để không bị lệch sau khi áp dụng thay đổi.
- Sơ đồ hệ thống Business AI Agents hiển thị riêng tại `/graph/system`, không trộn vào đồ thị nghiên cứu.
- Mỗi tài liệu đọc được có đồ thị tài liệu riêng; `Xem phân tích` mở đồ thị này và bảng kiểm tra nút hiển
  thị tóm tắt nguồn tối đa 200 ký tự, phần AI nghiên cứu độc lập và phần so sánh khác biệt.
- AI chỉ chuẩn bị bộ thay đổi đồ thị ở dạng nháp; kiểm tra/kiểm duyệt/phê duyệt/áp dụng vẫn bắt buộc.

Lộ trình triển khai:

1. Bản chiếu đồ thị trong bộ nhớ hoặc truy vấn cơ sở dữ liệu trước.
2. Bộ chuyển đổi Neo4j tạo lại thủ công, có tính lũy đẳng cho chế độ quan hệ/phân cấp đã hoàn thành và
   được kiểm chứng trên máy chủ thật; chỉ thêm đồng bộ outbox tự động khi có yêu cầu rõ về độ mới dữ liệu.

Tiêu chí nghiệm thu:

- Nghiên cứu đã duyệt xuất hiện trong đồ thị.
- Thẻ/khái niệm trở thành nút.
- Quan hệ thủ công trở thành cạnh.
- Bấm nút mở bảng chi tiết.
- Chế độ quan hệ/phân cấp có cùng tập nút và mặc định hỗ trợ tối đa 1.000 nút/4.000 cạnh.
- Tệp tải lên đọc được luôn có đồ thị tài liệu độc lập, kể cả khi điểm phù hợp thấp.
- Sơ đồ hệ thống có đường dẫn riêng và không xuất hiện trong chế độ quan hệ/phân cấp của nghiên cứu.

---

## Giai đoạn 5 - AI làm giàu dữ liệu

Mục tiêu: AI hỗ trợ xử lý nghiên cứu.

Chức năng:

- Tóm tắt nội dung.
- Trích xuất khái niệm.
- Gợi ý thẻ.
- Gợi ý quan hệ.
- Tạo embedding.

Phần máy chủ:

- Giao diện lập trình `LLMProvider`.
- Nhà cung cấp Ollama.
- Bản thay thế nhà cung cấp có kết quả xác định chỉ nằm trong bộ kiểm thử, không đăng ký khi ứng dụng chạy.
- Bảng/siêu dữ liệu nguồn gốc AI.
- Tác vụ nền hoặc tác vụ đồng bộ tùy MVP.

Thông tin nguồn gốc AI cần lưu:

- `model_name`
- `model_version`
- `prompt_version`
- `input_hash`
- `output_json`
- `confidence`
- `created_at`

Giao diện:

- Nút `Tóm tắt`.
- Nút `Trích xuất khái niệm`.
- Bảng gợi ý AI.
- Chấp nhận, từ chối hoặc sửa thẻ và quan hệ được gợi ý.

Tiêu chí nghiệm thu:

- Trường do AI tạo được phân biệt rõ với trường do con người tạo.
- Phần con người sửa không bị AI tự động ghi đè.
- Có thể chạy lại bước làm giàu dữ liệu.

---

## Giai đoạn 6 - MVP bộ thu thập tự động

Mục tiêu: tự động tiếp nhận từ một nguồn đơn giản.

Nguồn đầu tiên đề xuất:

- Nguồn tin RSS.

Lý do:

- Dễ chạy cục bộ.
- Ít phụ thuộc khóa API.
- Phù hợp với blog, tài liệu và tin tức về tác nhân AI.

Vòng đời bộ thu thập:

1. Phát hiện.
2. Tải.
3. Chuẩn hóa.
4. Khử trùng lặp.
5. Đánh giá.
6. Tự duyệt/đưa vào hàng chờ/từ chối.
7. Tiếp nhận.
8. Làm giàu dữ liệu.
9. Đồng bộ chỉ mục/tìm kiếm/đồ thị.

Phần máy chủ:

- CRUD nguồn thu thập.
- Chạy nguồn thủ công.
- Lịch sử chạy.
- Hàng chờ kiểm duyệt.
- Duyệt/từ chối/sửa rồi duyệt.

Giao diện:

- Trình quản lý bộ thu thập.
- Tình trạng nguồn.
- Hàng chờ kiểm duyệt.
- Chi tiết điểm số.

Ngưỡng mặc định:

- Tự duyệt: điểm >= 80.
- Cần kiểm duyệt: điểm 50-79.
- Từ chối: điểm < 50.

Tiêu chí nghiệm thu:

- Thêm nguồn RSS.
- Chạy bộ thu thập thủ công.
- Các mục được phát hiện và đánh giá.
- Mục đã duyệt trở thành mục nghiên cứu.

---

## Giai đoạn 7 - Phân tích khoảng trống và nghiên cứu sâu

Mục tiêu: chỉ triển khai sau khi kho tri thức, tìm kiếm và đồ thị đã ổn định.

Chức năng:

- Chỉ số độ phủ đồ thị.
- Phát hiện khoảng trống tri thức.
- Không gian xử lý khoảng trống.
- Giao cho nhà nghiên cứu.
- Yêu cầu AI nghiên cứu sâu.
- Con người phê duyệt trước khi xuất bản.
- Bản tin tuần.

Tiêu chí nghiệm thu:

- Hệ thống gợi ý khoảng trống dựa trên độ phủ.
- Con người có thể bỏ qua, giao việc hoặc yêu cầu nghiên cứu sâu.
- Báo cáo nghiên cứu sâu đi qua vòng đời kiểm duyệt trước khi được phê duyệt.

---

## 4. Mô hình dữ liệu v1

### Các bảng lõi

- `users`
- `research_items`
- `research_versions`
- `tags`
- `research_tags`
- `research_relations`
- `attachments`
- `comments`
- `audit_events`
- `outbox_events`

### Các bảng tìm kiếm/AI

- `embedding_chunks`
- `search_vector_projections`
- `ai_outputs`

### Các bảng bộ thu thập

- `collector_sources`
- `collector_runs`
- `discovered_items`
- `evaluations`

---

## 5. Bề mặt API v1

### Nghiên cứu

```text
GET    /api/v1/research
POST   /api/v1/research
GET    /api/v1/research/{id}
PUT    /api/v1/research/{id}
DELETE /api/v1/research/{id}
POST   /api/v1/research/{id}/submit-review
POST   /api/v1/research/{id}/approve
POST   /api/v1/research/{id}/archive
GET    /api/v1/research/{id}/versions
GET    /api/v1/research/{id}/relations
POST   /api/v1/research/{id}/relations
POST   /api/v1/research/{id}/attachments
```

### Tìm kiếm

```text
GET    /api/v1/search?q=
POST   /api/v1/search/semantic
GET    /api/v1/search/suggest?q=
GET    /api/v1/research/{id}/related
```

### Đồ thị

```text
GET    /api/v1/graph
GET    /api/v1/graph/system
GET    /api/v1/graph/node/{id}
GET    /api/v1/graph/ego/{id}
GET    /api/v1/graph/path?from=&to=
GET    /api/v1/graph/stats
POST   /api/v1/graph/rebuild
POST   /api/v1/documents/{id}/graph/research
```

### AI

```text
POST   /api/v1/ai/summarize
POST   /api/v1/ai/extract-concepts
POST   /api/v1/ai/suggest-relations
POST   /api/v1/ai/enrich/{research_id}
```

### Bộ thu thập

```text
GET    /api/v1/collector/sources
POST   /api/v1/collector/sources
PUT    /api/v1/collector/sources/{id}
POST   /api/v1/collector/sources/{id}/run
GET    /api/v1/collector/runs
GET    /api/v1/collector/review-queue
POST   /api/v1/collector/review-queue/{id}/approve
POST   /api/v1/collector/review-queue/{id}/reject
```

## 6. Các màn hình giao diện

### Màn hình MVP

- Tổng quan.
- Danh sách nghiên cứu.
- Chi tiết nghiên cứu.
- Trình soạn nghiên cứu.
- Trang tìm kiếm.
- Trình xem đồ thị.
- Cài đặt/quản trị cơ bản.

### Màn hình từ Giai đoạn 2 trở đi

- Trình quản lý bộ thu thập.
- Hàng chờ kiểm duyệt.
- Không gian xử lý khoảng trống.

---

## 7. Kế hoạch kiểm thử

### Kiểm thử đơn vị

- Chuyển trạng thái nghiên cứu.
- Tạo bản chụp phiên bản.
- Chuẩn hóa thẻ.
- Kiểm tra quan hệ.
- Phân tích truy vấn tìm kiếm.
- Khử trùng lặp của bộ thu thập.

### Kiểm thử API

- CRUD nghiên cứu.
- Gửi duyệt/phê duyệt/lưu trữ.
- Tìm kiếm/lọc.
- Cấu trúc điểm cuối đồ thị.
- AI làm giàu dữ liệu bằng bản thay thế có kết quả xác định tại ranh giới kiểm thử.
- Bộ thu thập duyệt/từ chối.

### Kiểm thử tích hợp

- Ghi Postgres/SQLite → bản chiếu tìm kiếm.
- Ghi nghiên cứu → bản chiếu đồ thị.
- Siêu dữ liệu tải tệp đính kèm cùng thao tác ghi, đọc, xóa và hoàn tác tương thích qua tuyến cục bộ/MinIO.
- Thử lại sự kiện outbox/tính lũy đẳng.
- Chạy bộ thu thập → mục được phát hiện → mục nghiên cứu đã tiếp nhận.

### Kiểm thử đầu-cuối

- Tạo bản nháp → duyệt → xuất hiện trong tìm kiếm.
- Tạo quan hệ → xuất hiện trong đồ thị.
- Chạy AI tóm tắt → chấp nhận bản tóm tắt.
- Mục RSS từ bộ thu thập → duyệt → xuất hiện trong thư viện.

---

## 8. Thiết kế nhật ký bàn giao AI

Mục tiêu: tạo cơ chế nhật ký chuẩn để khi hết hạn mức hoặc đổi tác nhân AI, tác nhân mới có thể
tiếp quản nhanh mà không cần đọc lại toàn bộ lịch sử trò chuyện.

### 8.1. Nguyên tắc

- Nhật ký phải nằm trong kho mã để mọi tác nhân đều đọc được.
- Nhật ký phải ngắn, có cấu trúc và được cập nhật sau mỗi phiên làm việc lớn.
- Nhật ký không thay thế tài liệu chính; nó thể hiện trạng thái vận hành hiện tại.
- Nhật ký phải ghi rõ việc đã làm, việc đang dở, quyết định đã chốt và vùng không được sửa.
- Không lưu bí mật, token, thông tin xác thực hay PII khách hàng trong nhật ký.

### 8.2. Tệp đề xuất

Tạo thư mục:

```text
AI_LOGS/
├── HANDOFF.md                  # trạng thái mới nhất, tác nhân nào cũng đọc đầu tiên
├── DECISIONS.md                # quyết định kỹ thuật/sản phẩm đã chốt
├── TASKS.md                    # danh sách công việc và trạng thái
├── SESSIONS/
│   └── 2026-07-09-session-001.md
└── TEMPLATES/
    ├── handoff-template.md
    └── session-template.md
```

Quy ước đọc:

1. Tác nhân mới đọc `AI_LOGS/HANDOFF.md`.
2. Nếu cần lý do quyết định, đọc `AI_LOGS/DECISIONS.md`.
3. Nếu cần lịch sử chi tiết, đọc nhật ký phiên gần nhất trong `AI_LOGS/SESSIONS/`.
4. Sau khi làm xong, tác nhân cập nhật `HANDOFF.md` và tạo nhật ký phiên mới.

### 8.3. Định dạng HANDOFF.md

```markdown
# Nhật ký bàn giao AI

## Mục tiêu hiện tại
- Mục tiêu hiện tại:
- Người yêu cầu:
- Trạng thái: đang lập kế hoạch / đang triển khai / bị chặn / sẵn sàng kiểm duyệt

## Trạng thái hiện tại
- Kho mã hiện có:
- Tệp quan trọng:
- Chạy ứng dụng bằng:
- Chạy kiểm thử bằng:

## Đã hoàn thành
- [x] Việc đã hoàn thành

## Đang thực hiện
- [ ] Việc đang làm dở
- Tệp liên quan:
- Nhánh/commit nếu có:

## Hành động tiếp theo phù hợp nhất
1. Việc nên làm tiếp theo
2. Việc tiếp theo sau đó

## Quyết định đã chốt
- Không tự đổi quyết định đã chốt nếu chưa hỏi người dùng.

## Không được thay đổi
- Tệp/khu vực không được sửa.
- Thay đổi của người dùng chưa bị hoàn nguyên.

## Vấn đề đã biết
- Lỗi/rủi ro/trở ngại hiện tại.

## Xác minh
- Lệnh đã chạy:
- Kết quả:
- Lệnh chưa chạy được:
```

### 8.4. Định dạng nhật ký phiên

Mỗi tác nhân khi kết thúc một lượt làm việc đáng kể tạo một tệp trong `AI_LOGS/SESSIONS/`.

Tên file:

```text
YYYY-MM-DD-HHMM-agent-short-summary.md
```

Template:

```markdown
# Nhật ký phiên

## Bối cảnh
- Yêu cầu của người dùng:
- Tác nhân:
- Ngày/giờ:

## Công việc đã làm
- Tệp đã thay đổi:
- Hành vi đã thay đổi:
- Lệnh đã chạy:

## Lập luận / Quyết định
- Quyết định:
- Lý do:
- Phương án đã cân nhắc:

## Xác minh
- Kiểm thử/kiểm tra:
- Kết quả:

## Ghi chú cho tác nhân tiếp theo
- Tiếp tục từ:
- Cần lưu ý:
- Lệnh tiếp theo đề xuất:
```

### 8.5. Định dạng TASKS.md

`TASKS.md` giúp tác nhân mới không phải tự suy luận danh sách công việc còn lại.

```markdown
# Bảng công việc

## Hiện tại
- [ ] Công việc ưu tiên cao nhất

## Tiếp theo
- [ ] Công việc tiếp theo

## Sau này
- [ ] Công việc sau MVP

## Bị chặn
- [ ] Công việc bị chặn
  - Trở ngại:
  - Cần người dùng quyết định:

## Hoàn thành
- [x] Công việc đã xong
```

### 8.6. Định dạng DECISIONS.md

`DECISIONS.md` là nhật ký ADR gọn nhẹ.

```markdown
# Các quyết định

## DEC-001 - MVP ưu tiên cục bộ
- Ngày:
- Trạng thái: đã chấp nhận
- Quyết định:
- Lý do:
- Hệ quả:
```

### 8.7. Quy trình tác nhân bắt đầu làm việc

Tác nhân mới phải làm theo thứ tự:

1. Đọc `AI_LOGS/HANDOFF.md`.
2. Đọc `AI_LOGS/TASKS.md`.
3. Đọc `AI_LOGS/DECISIONS.md` nếu task có ảnh hưởng kiến trúc.
4. Kiểm tra `git status --short`.
5. Đọc các tệp liên quan trước khi sửa.
6. Không hoàn nguyên thay đổi của tác nhân/người dùng trước nếu không được yêu cầu.
7. Làm công việc nhỏ nhất có thể hoàn thành.
8. Chạy xác minh.
9. Cập nhật nhật ký bàn giao.

### 8.8. Quy trình tác nhân kết thúc phiên

Trước khi kết thúc hoặc khi gần hết hạn mức:

1. Ghi rõ việc đã làm.
2. Ghi các tệp đã sửa.
3. Ghi các lệnh/kiểm thử đã chạy.
4. Ghi lỗi còn lại.
5. Ghi hành động tiếp theo phù hợp nhất.
6. Ghi những việc không được làm tiếp nếu chưa hỏi người dùng.
7. Nếu có thay đổi mã, ghi trạng thái git ngắn gọn.

### 8.9. Tích hợp vào Hệ thống nghiên cứu sau này

Khi ứng dụng đã có phần máy chủ, nhật ký bàn giao AI có thể trở thành một phần của Hệ thống nghiên cứu.

Thực thể đề xuất:

- `AgentSession`
- `AgentDecision`
- `AgentTask`
- `AgentHandoff`
- `VerificationRun`

API đề xuất:

```text
GET    /api/v1/agent-handoff/current
POST   /api/v1/agent-handoff/sessions
POST   /api/v1/agent-handoff/decisions
GET    /api/v1/agent-handoff/tasks
PUT    /api/v1/agent-handoff/tasks/{id}
```

Nhưng trong MVP hiện tại, dùng tệp Markdown đã đủ nhanh, ít phụ thuộc và dễ dùng giữa nhiều tác nhân AI.

### 8.10. Tiêu chí nghiệm thu

- Tác nhân mới chỉ cần đọc `AI_LOGS/HANDOFF.md` và `AI_LOGS/TASKS.md` để biết nên làm gì tiếp.
- Mỗi phiên làm việc quan trọng có nhật ký phiên.
- Mọi quyết định kiến trúc có mục tương ứng trong `DECISIONS.md`.
- Nhật ký không chứa bí mật hay PII.
- Nhật ký luôn nói rõ đã chạy xác minh hay chưa.

---

## 9. Tiêu chí nghiệm thu MVP

MVP được xem là đạt khi:

- Ứng dụng chạy cục bộ theo hướng dẫn rõ ràng.
- Người dùng tạo, sửa và duyệt nghiên cứu được.
- Nghiên cứu đã duyệt có thể tìm kiếm được.
- Nghiên cứu đã duyệt xuất hiện trong đồ thị.
- Bước AI làm giàu dữ liệu chạy được bằng nhà cung cấp thật đã cấu hình hoặc Ollama cục bộ.
- Có dữ liệu mẫu để minh họa.
- Có kiểm thử cho API lõi.
- Tài liệu thiết lập và kiến trúc được cập nhật theo triển khai thực tế.
- Có nhật ký bàn giao AI để tác nhân khác tiếp quản khi đổi tác nhân hoặc hết hạn mức.

---

## 10. Rủi ro và cách giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| Phạm vi quá lớn | Bám MVP kho tri thức nghiên cứu trước, làm nền tảng bộ thu thập sau |
| Neo4j/Meilisearch khiến thiết lập cục bộ nặng | Cho phép dùng bản chiếu gọn nhẹ trước |
| Ollama chậm hoặc thiếu mô hình | Chọn nhà cung cấp thật khác, báo rõ trạng thái chưa sẵn sàng và dùng tác vụ bất đồng bộ |
| Đầu ra AI sai | Con người chấp nhận/từ chối, lưu nguồn gốc |
| Bộ thu thập tạo dữ liệu rác | Dùng ngưỡng + hàng chờ kiểm duyệt + khử trùng lặp |
| Đổi tác nhân AI làm mất ngữ cảnh | Bắt buộc cập nhật `AI_LOGS/HANDOFF.md` và nhật ký phiên |
| Tác nhân mới sửa nhầm vùng đang dở | Dùng mục `Không được thay đổi` và `Đang thực hiện` trong nhật ký bàn giao |

---

## 11. Thứ tự thực hiện đề xuất

1. Hoàn thiện các tệp đặc tả trong `Docs/`.
2. Tạo `AI_LOGS/` gồm bàn giao, quyết định, công việc và mẫu nhật ký phiên.
3. Tạo khung phần máy chủ + cơ sở dữ liệu.
4. Triển khai CRUD nghiên cứu.
5. Triển khai thư viện/trình soạn nghiên cứu trên giao diện.
6. Triển khai tìm kiếm.
7. Triển khai bản chiếu đồ thị.
8. Triển khai AI làm giàu dữ liệu bằng Ollama và các nhà cung cấp đám mây đã cấu hình.
9. Triển khai MVP bộ thu thập RSS.
10. Hoàn thiện màn hình tổng quan, kiểm thử và tài liệu.

---

## 12. Ghi chú triển khai

- Không triển khai toàn bộ nền tảng ngay từ đầu.
- Không để AI tự động ghi đè các trường do con người chỉnh sửa.
- Không dùng Neo4j làm nguồn dữ liệu chuẩn.
- Không phụ thuộc nhà cung cấp đám mây trong MVP.
- Mọi bản chiếu phải tạo lại được từ cơ sở dữ liệu chính.
- Mỗi tác nhân AI phải cập nhật nhật ký bàn giao trước khi dừng nếu đã thay đổi mã/tài liệu.
