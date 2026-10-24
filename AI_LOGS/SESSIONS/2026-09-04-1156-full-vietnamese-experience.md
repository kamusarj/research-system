# Nhật ký phiên làm việc

## Bối cảnh

- Yêu cầu của người dùng: Chuyển toàn bộ dự án sang tiếng Việt hợp lý, không quá học thuật cũng không quá
  đơn giản, để thuận tiện nghiên cứu.
- Agent: Codex
- Ngày/giờ: 2026-09-04 11:56 +07

## Công việc đã làm

- Tệp đã thay đổi:
  - Web: từ điển/ngữ cảnh ngôn ngữ, app shell, metadata, các trang và thành phần tài liệu, nhập
    liệu, đồ thị, chat, khoảng trống nghiên cứu, lỗi an toàn và các kiểm thử liên quan dưới
    `apps/web/`.
  - API: thêm `apps/api/app/core/localization.py`; Việt hoá phản hồi an toàn và nội dung do hệ
    thống tạo trong auth, tài liệu, nguồn, đồ thị, chat, collector, runtime/CLI và các kiểm thử.
  - Discord: cố định tiếng Việt và Việt hoá bot, gateway, hướng dẫn, thông báo, README, mô tả gói
    cùng kiểm thử dưới `apps/discord-bot/`.
  - Tài liệu: `README.md`, `apps/README.md`, `Docs/Research System MVP Specification.md`,
    `Docs/Research System Implementation Plan.md`, `Docs/Research System Completion Plan.md`,
    `Docs/Business AI Agents Completion Goal.md` và tài liệu mới
    `Docs/Quy uoc ngon ngu tieng Viet.md`.
  - Harness/log: story `US-FULL-VIETNAMESE-EXPERIENCE`, decision 0044/DEC-057 và các tệp bàn giao.
- Hành vi đã thay đổi:
  - Sản phẩm chỉ dùng tiếng Việt; bỏ bộ chuyển EN/VI và khai báo trang là `lang="vi"`.
  - Các nhãn, trạng thái, trợ năng và thông báo an toàn dùng văn phong rõ, tự nhiên cho nghiên cứu.
  - Giữ nguyên định danh kỹ thuật, hợp đồng API, mã lỗi, tên công nghệ và nội dung nguồn/người dùng.
- Lệnh đã chạy:
  - `bash scripts/bootstrap-harness.sh`
  - `scripts/bin/harness-cli query matrix --active --summary`
  - `npm run lint`, `npm run typecheck`, `npm test -- --run`, `npm run build` trong `apps/web`
  - `.venv/bin/python -m ruff check .` và `.venv/bin/python -m pytest -q` trong `apps/api`
  - `.venv/bin/python -m ruff check .` và `.venv/bin/python -m pytest -q` trong
    `apps/discord-bot`
  - Playwright cho 45 ca ngôn ngữ trọng yếu trên desktop, tablet và mobile
  - Kiểm tra tĩnh chuỗi hiển thị, cấu trúc/hàng rào mã Markdown và `git diff --check`

## Lập luận và quyết định

- Quyết định: tiếng Việt là ngôn ngữ duy nhất trên các bề mặt sản phẩm đang phát hành.
- Lý do: một hệ thuật ngữ thống nhất giúp người nghiên cứu đọc nhanh và hiểu đúng hơn so với giao
  diện song ngữ trộn thuật ngữ.
- Phương án đã cân nhắc:
  - Giữ nút chuyển sang tiếng Anh: không chọn vì không đáp ứng yêu cầu sản phẩm hoàn toàn tiếng Việt.
  - Dịch cả định danh kỹ thuật và dữ liệu gốc: không chọn vì có thể phá hợp đồng tích hợp và làm sai
    nguồn gốc nghiên cứu.

## Kiểm chứng

- Kiểm thử/kiểm tra:
  - Frontend: ESLint, TypeScript, 33 tệp / 145 Vitest, build Next.js 15 route.
  - API: Ruff, 323 Pytest.
  - Discord: Ruff, 55 Pytest.
  - E2E: 45 Playwright trên ba kích thước màn hình.
  - Tĩnh: từ điển tiếng Việt hiệu lực, tài liệu cốt lõi, Markdown fences, `git diff --check`.
- Kết quả: tất cả đều đạt. API còn một cảnh báo Starlette/httpx đã tồn tại từ trước; không có lỗi
  kiểm thử. Một lượt E2E ban đầu phát hiện selector tiếng Anh cũ và mock auth thiếu; đã sửa và lượt
  cuối đạt 45/45. Harness đã đóng story ở trạng thái `implemented`; detailed trace #4 đạt 3/3.

## Ghi chú cho phiên tiếp theo

- Tiếp tục từ: story `US-FULL-VIETNAMESE-EXPERIENCE` đã hoàn tất; dùng
  `Docs/Quy uoc ngon ngu tieng Viet.md` khi thêm nội dung mới.
- Lưu ý: không dịch hồi tố AI logs, migration, dữ liệu nguồn/người dùng hoặc định danh kỹ
  thuật; chúng được giữ để bảo toàn provenance và hợp đồng máy.
- Lệnh tiếp theo được đề xuất: kiểm tra dung lượng đĩa trước khi rebuild Docker; bản dựng frontend cục bộ
  và toàn bộ test hiện đã đạt.
