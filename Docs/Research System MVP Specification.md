# Đặc tả MVP của Hệ thống nghiên cứu

Tài liệu này chuyển `Research System Implementation Plan.md` thành hợp đồng triển khai cụ thể cho hệ thống ưu tiên chạy cục bộ.

## Phạm vi sản phẩm

MVP cho phép một nhóm nhỏ tạo tài liệu nghiên cứu Markdown, đưa tài liệu qua quy trình kiểm duyệt, tìm tri thức đã duyệt, xem đồ thị, làm giàu nội dung bằng nhà cung cấp AI và tiếp nhận mục RSS.

Ngoài phạm vi: SSO cho môi trường thật, triển khai đám mây, Kubernetes, thu thập hàng loạt từ nhiều nguồn và tác nhân nghiên cứu sâu tự chủ.

## Vòng đời nghiên cứu

Các bước chuyển trạng thái được phép:

```text
draft -> in-review -> approved -> archived
   ^          |
   +----------+
```

Mỗi lần cập nhật một mục hiện có đều tạo bản chụp phiên bản. Bản ghi lưu trữ chỉ bị xóa mềm và vẫn có thể truy cập bằng ID. Tóm tắt và thẻ do con người sửa chỉ thay đổi khi API nhận yêu cầu rõ ràng; kết quả AI được lưu riêng cho đến khi người dùng chấp nhận.

## Siêu dữ liệu bắt buộc

- Bắt buộc: `title`, `type`, `collection_method`.
- Không bắt buộc: `summary`, nội dung Markdown `content`, `source_url`, `authors`, `tags` và JSON `metadata` tùy ý.
- Loại tài liệu: `internal-research`, `reference`, `deep-research-report`.
- Cách thu thập: `manual`, `auto-collected`, `ai-researched`.

Xác thực và phân quyền theo vai trò được hoãn trong phạm vi ban đầu. Điểm cuối duyệt đại diện cho thao tác của nhà nghiên cứu có quyền trong MVP cục bộ dành cho một nhóm.

## Hành vi tìm kiếm và đồ thị

- Kết quả thư viện và tìm kiếm mặc định không gồm mục đã lưu trữ.
- Tìm kiếm không phân biệt hoa thường trên tiêu đề, tóm tắt, nội dung, tác giả và thẻ đã chuẩn hóa.
- Bộ lọc kết hợp với phân trang, hỗ trợ trạng thái, loại, cách thu thập, thẻ và ngày tạo.
- Bản chiếu đồ thị gồm nút nghiên cứu đã duyệt, nút thẻ/khái niệm đã chuẩn hóa, nút tác giả, nút nguồn thu thập và quan hệ nghiên cứu thủ công.
- Trong MVP, đồ thị được dựng lại từ cơ sở dữ liệu chính theo mỗi yêu cầu và sau này có thể chiếu sang Neo4j.

## Hành vi AI

- Mistral là nhà cung cấp mặc định; có thể chọn Ollama hoặc nhà cung cấp đám mây khác qua cấu hình môi trường.
- Ứng dụng không có nhà cung cấp AI giả chạy trong tiến trình. Nếu chưa cấu hình được nhà cung cấp thật hoặc không thể kết nối, thao tác AI sẽ tạm khóa và báo rõ trạng thái.
- Mỗi đầu ra lưu nguồn gốc mô hình/câu lệnh, mã băm đầu vào, JSON đầu ra, độ tin cậy và thời điểm tạo.
- AI không bao giờ tự ghi đè trường do con người biên tập.

## Hành vi bộ thu thập

- RSS là bộ điều hợp nguồn duy nhất trong phạm vi MVP ban đầu.
- Một lượt chạy thủ công sẽ phát hiện và chuẩn hóa mục, loại trùng theo nguồn/ID ngoài và URL, đánh giá theo quy tắc xác định rồi định tuyến theo ngưỡng cấu hình.
- Điểm `>= auto_approve_threshold` sẽ được tiếp nhận; điểm dưới `auto_reject_threshold` bị từ chối; phần còn lại vào hàng chờ duyệt.

## Nghiệm thu cục bộ

1. `docker compose up --build` khởi động PostgreSQL, API và giao diện web.
2. Kiểm tra sức khỏe API thành công và giao diện gọi được API.
3. Có thể tạo, gửi duyệt, phê duyệt, tìm kiếm bản nháp nghiên cứu và xem nó trong đồ thị.
4. Mỗi lần chỉnh sửa tạo một bản chụp phiên bản.
5. Việc làm giàu bằng nhà cung cấp thật lưu nguồn gốc và trả đề xuất mà không ghi đè nghiên cứu.
6. Có thể duyệt hoặc tiếp nhận các mục RSS.
7. Kiểm thử backend, kiểm tra lint/kiểu của frontend và bản dựng production đều đạt.
