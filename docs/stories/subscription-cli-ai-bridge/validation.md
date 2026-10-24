# Validation

## Proof Strategy

Chứng minh mỗi CLI trả JSON đúng schema khi chạy không tương tác, Codex/agy không thấy tệp
của chủ máy, container chỉ gọi được cầu nối bằng token, lỗi CLI ánh xạ đúng mã cũ, và chat
đồ thị đi hết vòng công cụ với nhà cung cấp CLI.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit (bridge) | strict schema/nullable/bỏ null, trích JSON, phân loại lỗi, kiểm tra request, dạng lệnh bwrap, Claude không công cụ/không API key, Codex strict + thử lại không schema, agy stream-json, HTTP token/health |
| Unit (API) | provider gửi đúng backend/model/effort/schema, mã lỗi tác vụ nền, liệt kê + preflight, chat tool call, công cụ lạ/tham số sai, mã lỗi chat, không nhận khóa cá nhân |
| Regression | Toàn bộ API pytest; frontend tsc, ESLint, vitest chat/lib |
| Live | `probe` từng backend trên máy; kiểm tra cô lập sandbox bằng canary; container → bridge (token đúng/sai); Codex từ container: phân loại link, trích đồ thị, chat 2 lượt có công cụ |
| Runtime | service bridge active, API/worker tạo lại với `AI_PROVIDER=codex`, frontend healthy, tunnel `/chat` 200 |

## Fixtures

CLI giả qua `run_process` bị thay thế và HTTP giả; thử thật chỉ dùng prompt tổng hợp, không ghi
database.

## Acceptance Evidence

- 46/46 test mới (`test_ai_cli_bridge.py`, `test_cli_providers.py`); toàn bộ API 420/420 đạt;
  Ruff sạch. Frontend: `tsc --noEmit`, ESLint, vitest 55/55 (chat + lib).
- Probe thật: Claude Code `sonnet` 3,4 giây; Codex `gpt-6-luna` low 8,1 giây trong sandbox;
  Antigravity `gemini-3.8-flash-medium` 16–30 giây (lần đầu 62 giây) trong sandbox.
- Sandbox: không đọc được canary trong home, không có repo, không có `/run/docker.sock`,
  môi trường chỉ PATH/HOME/LANG/TERM; `~/.codex/auth.json` không bị thay inode.
- Container API gọi `/v1/health` 200 với token, 401 với token sai; cầu nối không nghe loopback.
- Codex từ container: LinkClassification 8,4 giây (bỏ qua câu lệnh chèn trong nội dung),
  DocumentGraphExtraction strict 8,2 giây, chat lượt 1 gọi `search_graph`, lượt 2 trả lời
  tiếng Việt từ kết quả công cụ.
- Runtime: `/ai/providers` báo codex active + chat_active, cả ba CLI configured/reachable;
  frontend rebuild healthy; tunnel `/chat` 200.
