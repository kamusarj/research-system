# 0044 Tiếng Việt là ngôn ngữ duy nhất của sản phẩm

Ngày: 2026-09-04

## Trạng thái

Đã chấp nhận

## Bối cảnh

Sản phẩm trước đây coi tiếng Anh và tiếng Việt là hai ngôn ngữ ngang hàng. Cách làm này khiến giao
diện mặc định vẫn là tiếng Anh, đồng thời nhiều nhãn tiếng Việt bị trộn các từ như “workspace”,
“pipeline”, “graph”, “node”, “provider” và “draft”. Chủ sản phẩm yêu cầu toàn bộ trải nghiệm chuyển
sang tiếng Việt dễ đọc để phục vụ nghiên cứu, nhưng vẫn phải đủ chính xác về mặt kỹ thuật.

## Quyết định

Tiếng Việt là ngôn ngữ duy nhất trên các bề mặt do sản phẩm phát hành: giao diện web, nội dung trợ
năng, thông báo lỗi an toàn, phản hồi của cổng Discord và tài liệu hướng dẫn chính. Bộ chuyển EN/VI
được gỡ bỏ và tài liệu HTML khai báo `lang="vi"`.

Giữ nguyên tên riêng, tên công nghệ, mã lỗi, đường dẫn API, khóa JSON, tên biến, tên mô hình/nhà cung
cấp và dữ liệu nghiên cứu gốc. Thuật ngữ khó được diễn đạt bằng tiếng Việt rõ nghĩa; chỉ giữ từ gốc
hoặc chữ viết tắt khi đó là cách gọi quen thuộc và chính xác hơn.

## Phương án đã cân nhắc

1. Chỉ đổi ngôn ngữ mặc định sang tiếng Việt nhưng giữ nút chuyển sang tiếng Anh. Không chọn vì vẫn
   cho phép sản phẩm quay lại một bề mặt không đáp ứng yêu cầu “hoàn toàn bằng tiếng Việt”.
2. Dịch cả định danh kỹ thuật và dữ liệu đã lưu. Không chọn vì sẽ phá hợp đồng API, khả năng truy vết
   lỗi và tính nguyên vẹn của tài liệu nghiên cứu.

## Hệ quả

Điểm tích cực:

- Người nghiên cứu có một hệ thuật ngữ nhất quán, dễ đọc trên mọi luồng chính.
- Không còn trạng thái nhấp nháy tiếng Anh khi ứng dụng tải hoặc khi trình duyệt từng lưu locale cũ.
- Mã lỗi và định danh kỹ thuật vẫn có thể dùng để tra cứu, kiểm thử và tích hợp.

Đánh đổi:

- Người dùng không còn chuyển giao diện sang tiếng Anh.
- Nội dung do nguồn bên ngoài hoặc người dùng cung cấp vẫn có thể ở ngôn ngữ gốc; sản phẩm không tự
  dịch dữ liệu nghiên cứu vì điều đó có thể làm sai nghĩa và nguồn gốc.
- Các log lịch sử, story cũ và migration được giữ nguyên như bằng chứng; chúng không phải bề mặt sản
  phẩm đang phát hành.

## Việc tiếp theo

- Dùng kiểm tra tĩnh và test giao diện để ngăn chuỗi tiếng Anh không chủ ý quay trở lại.
- Khi thêm nhãn mới, tham chiếu tài liệu thuật ngữ tiếng Việt của dự án.
