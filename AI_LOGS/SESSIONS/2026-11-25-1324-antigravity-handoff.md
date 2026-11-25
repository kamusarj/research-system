# Bàn giao dự án cho Antigravity

Ngày 2026-11-25, Asia/Bangkok. Codex, Harness intake 37. Linh yêu cầu ghi việc còn lại để
Antigravity tiếp tục vì phiên hiện tại sắp hết hạn mức.

## Điểm bắt đầu

- Tiếp tục trong `/home/linh/Desktop/Business AI Agents` trên nhánh `feature/research-system-mvp`.
  HEAD lúc bàn giao là `b9a3ffa`. Các thay đổi mới đang trong working tree, gồm cả tệp chưa được
  theo dõi. Đọc `AGENTS.md`, `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`
  theo thứ tự startup và xem `git status --short` trước khi sửa.
- Hai đợt audit, Weave và nền tảng model local đã `implemented` và có Harness verify `pass`.
  Story `US-OPTIMIZATION-PROGRAM` vẫn `in_progress` dù Harness verify đạt.
- Phiên gần nhất dọn `.env.example` còn 58 dòng. Cấu hình Compose render giống nhau ở bốn lượt
  kiểm tra. Xem [phiên dọn cấu hình](2026-11-25-1322-trim-env-example.md).

## Việc kỹ thuật ưu tiên

1. Tiếp tục `US-OPTIMIZATION-PROGRAM`. Đọc [quy trình đánh giá](../../docs/evaluations/research-agent/README.md)
   và [chứng cứ kiểm thử](../../docs/stories/optimization-program/validation.md). Mẫu mới nhất
   `q1-market-size` đạt 5/5 góc nhìn, 100% độ phủ trích dẫn và đủ usage ở cả hai biến thể. Kiểm thử
   đạt 935 ca API (4 bỏ qua) và 236 ca web. Mẫu một câu chưa đủ xác nhận mốc giảm 20% token.
2. Khi có yêu cầu chạy toàn bộ và provider còn hạn mức, chạy đủ tám câu cho `reference`, rồi
   `optimized`. Dùng cùng Codex `gpt-6-luna`, corpus cố định, cấu hình và mã nguồn. Khai báo
   `RESEARCH_EVAL_DATABASE_URL` cho PostgreSQL thử đã chạy migration và dùng
   `--stop-on-provider-error`. Với chẩn đoán giới hạn, repo hướng dẫn dùng tập con như
   `q3-platform-comparison`, `q4-architecture`, `q5-risk-compliance`, là các câu từng hụt góc nhìn.
3. Corpus công khai nằm ngoài repo tại
   `~/.cache/business-ai-agents/audit-runtime/research-corpus-20261119.json`. Artifact mẫu hiện
   tại nằm cùng thư mục cha, dưới `20261125-perspective-UOBkiS/`. Chạy `research-eval-compare`
   và giữ đủ usage, trích dẫn, góc nhìn cùng điều kiện độ phủ thực thể cho từng câu. Dùng trường
   `perspectives_with_verified_claims` và `perspectives_covered` để phân biệt thiếu bằng chứng
   với thiếu mục báo cáo. Lưu số đo và hash thay cho toàn văn corpus.
4. Nếu provider trả lỗi hạn mức, giữ artifact đã lưu và ghi mã lỗi. Có thể tiếp tục đọc artifact
   và chạy kiểm thử không gọi model trong lúc chờ. Kết quả cũ ngày 19/11 chỉ dùng chẩn đoán.

## Việc chờ Linh hoặc môi trường thật

- **Weave/Graph v2.** Linh nghiệm thu trên `http://localhost:13000`. Bao gồm đồ thị phân cấp,
  sơ đồ hệ thống, đồ thị tài liệu, kéo thả, nhãn và dark/light. Quyết định áp dụng các đề xuất
  đồ thị theo [checklist Graph v2](../../Docs/Graph%20Intelligence%20v2%20Product%20Acceptance%20Checklist.md)
  và mã draft trong `TASKS.md`.
- **CI/phát hành.** `.github/workflows/ci.yml` đã kiểm local, hiện chưa được Git theo dõi.
  Sau khi Linh quyết commit/push, theo dõi GitHub Actions và ghi kết quả CI thực tế. Các image
  `local-build-20261125` được build trước hai lượt sửa evaluator và độ phủ Research Agent.
- **Model local.** Operator cần Ollama hoặc LM Studio đã cài model thật, rồi kiểm tra chat/JSON
  qua `local-ai` và SSH/VPN nếu dùng máy khác. Việc kiểm thử cầu nối và UI đã có chứng cứ.
- **Provider và kết nối ngoài.** Gemini cần key trước khi đổi embedding và lập chỉ mục lại.
  OpenAI cần key hợp lệ, Claude cần kiểm billing, Mistral generation chờ tier/hạn mức phù hợp.
  ChatGPT plan cần Linh tự cấp OAuth consent, và bản web cần client ID. Discord thật cần bot
  token cùng guild/channel cho phép. Triển khai nhóm cần tên miền/HTTPS, backup ngoài máy cần
  đích và quyền truy cập. Chi tiết theo `TASKS.md`. Giữ bí mật trong cấu hình riêng của operator.
- **Vận hành tùy chọn.** Cache `uv` chỉ còn là việc phụ khi tiến trình đang dùng cache đã thoát.
  Kiểm tra dung lượng trước khi build ảnh lớn. Hàng chờ kỹ thuật dài hạn ở mục Later của `TASKS.md`.

## Tệp thay đổi và xác minh

- Cập nhật `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và thêm phiên log này. Phạm vi bàn giao qua
  tệp trong repo để Antigravity đọc trực tiếp.
- `git status`, `git log`, `df -h`, `stat` kiểm nhánh, dung lượng và sự hiện diện của corpus/artifact.
  Còn trống 9,1 GiB trên `/` và 5,3 GiB trên `/home`. API `/api/v1/health` ở `:18000` và
  `/graph` ở `:13000` trả HTTP 200.
- Bootstrap Harness, ghi intake 37, xem bảng story và `last_verified_result`. `git diff --check`
  xác minh phần bàn giao. Các số test và provider trong bản bàn giao trích từ phiên đã ghi log.
