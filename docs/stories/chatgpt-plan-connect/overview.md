# Overview

## Current Behavior

- Mọi việc AI dùng khóa API của máy chủ hoặc gói CLI của chủ máy (chỉ chế độ cục bộ, DEC-062).
- Không có cách để từng người dùng tự trả quota AI bằng tài khoản của họ.

## Target Behavior

- Trong trang Tài khoản, người dùng bấm "Tiếp tục với ChatGPT", đồng ý tại OpenAI và từ đó việc AI
  họ khởi chạy (link, tài liệu, nghiên cứu sâu, chat) tính vào hạn mức gói ChatGPT Plus/Pro của họ.
- Người dùng thấy đang dùng gói nào, chọn model trong danh mục của tài khoản, có liên kết "Quản lý
  mức dùng", ngắt hoặc xóa kết nối; hết hạn mức thì báo rõ, không tự chuyển sang khóa máy chủ.
- Chế độ cục bộ chạy được ngay; bản web bật khi OpenAI cấp client ID.

## Affected Users

- Owner, researcher (viewer không chạy AI).

## Affected Product Docs

- `README.md` (mục "Mỗi người dùng tự dùng gói ChatGPT"), `.env.example`, `.env.team.example`,
  `docs/decisions/0052-per-user-chatgpt-plan.md`.

## Non-Goals

- Embedding/RAG bằng gói ChatGPT (plan usage chỉ hỗ trợ Responses API).
- Bắt buộc mọi người dùng phải kết nối gói (để sau).
- Tải `auth.json` của Codex lên máy chủ.

## Validation

- `apps/api/tests/test_chatgpt_plan.py` (25 test: hợp đồng OAuth cục bộ/đối tác, PKCE, state một lần
  gắn người dùng, nonce, scope, mã hóa token, làm mới/xoay vòng, lỗi hạn mức, thu hồi, ai trả quota,
  chặn chạy lại gói người khác, log không lộ mã).
- `apps/web/components/chatgpt-plan-card.test.tsx`, `apps/web/app/account/ai/callback/page.test.tsx`.
- Kiểm chứng thật ở chế độ cục bộ bằng tài khoản ChatGPT của chủ sở hữu.
