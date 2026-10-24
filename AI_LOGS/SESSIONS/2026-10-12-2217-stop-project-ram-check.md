# Session: Tạm dừng Docker project và đo RAM

## Context

- User request: “tắt thử cho tôi docker đang chạy project này xem ram có giảm không”.
- Agent: Codex.
- Date/time: 2026-10-12, 22:17–22:19 Asia/Bangkok (UTC+7).
- Scope: thao tác runtime đã được yêu cầu; không triển khai/sửa tính năng repository.
  Không bootstrap, ghi intake hay trace Harness cho thao tác vận hành này.

## Work Done

- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` và session này.
- Behavior changed: dừng user service `business-ai-agents.service`, rồi dừng frontend,
  worker và API trước khi dừng PostgreSQL của Compose project `businessaiagents`.
- Giữ nguyên container, image, cấu hình restart, named volume và cấu hình autostart.
- Không thao tác lên project Docker khác; không restart stack sau khi đo.
- Commands run:
  - Đọc HANDOFF, TASKS, DECISIONS, AGENTS, template và tài liệu/runtime liên quan.
  - `docker ps --no-trunc --format '{{json .}}'`, `docker inspect` với các trường
    label/mount/state cụ thể, `systemctl --user cat/show business-ai-agents.service`.
  - `docker stats --no-stream --format '{{json .}}'` cho bốn container đích.
  - `free -b` trước dừng, ngay sau dừng và ba lần đo ổn định cách nhau 5 giây.
  - `systemctl --user stop business-ai-agents.service`.
  - `docker stop --timeout 30` cho ba ID container ứng dụng đã xác nhận label,
    sau đó cùng lệnh cho ID database.
  - `docker volume ls --filter label=com.docker.compose.project=businessaiagents`,
    `docker ps -q --filter label=com.docker.compose.project=businessaiagents`,
    kiểm tra trạng thái từng container và `ss -H -ltn`.

## Reasoning / Decisions

- Chỉ dừng container thuộc project này, giữ Docker daemon chạy vì máy còn project khác.
- Dùng stop để giữ nguyên container/volume; không dùng down, prune hay xóa dữ liệu.
- Dừng service trong phiên hiện tại để trạng thái systemd phản ánh runtime đã tắt;
  không disable autostart vì người dùng chỉ yêu cầu thử tắt.
- Dùng RAM used/available của `free -b` để so sánh trên host, đồng thời ghi Docker stats
  làm đối chiếu; không xóa cache hay can thiệp bộ nhớ hệ thống.

## Verification

| Thời điểm (UTC+7) | RAM used (byte) | RAM used (GiB) | Giảm so với trước (MiB) |
| --- | ---: | ---: | ---: |
| 22:17:54, trước dừng | 8612417536 | 8,021 | — |
| 22:18:25, ngay sau dừng | 7849316352 | 7,310 | 727,75 |
| 22:19:02 | 7723085824 | 7,193 | 848,13 |
| 22:19:07 | 7797694464 | 7,262 | 776,98 |
| 22:19:12, lần cuối | 7778201600 | 7,244 | 795,57 |

- RAM available tăng từ 7324561408 lên 8158777344 byte ở lần đo cuối.
- Docker stats trước dừng: frontend 84,07 MiB; worker 95,88 MiB;
  API 543,1 MiB; PostgreSQL 35,57 MiB; tổng 758,62 MiB.
- Bốn container đích đều `exited`, giữ nguyên ID; không còn container đang chạy mang
  label project `businessaiagents`. Frontend/API/database exit 0; worker exit 137.
- Service: `ActiveState=inactive`, `SubState=dead`, `UnitFileState=enabled`.
- Cổng `13000` và `18000` không còn lắng nghe.
- Bốn named volume trước/sau trùng nhau: `businessaiagents_document_objects`,
  `businessaiagents_frontend_modules`, `businessaiagents_frontend_next`,
  `businessaiagents_postgres_data`.
- Cả 10 container của project khác vẫn chạy với các ID ban đầu.
- Kiểm tra cuối: cấu trúc/hàng rào Markdown và `git diff --check` cho ba tệp log.
- Result: runtime đã tắt; RAM dùng trên host giảm khoảng 0,76–0,83 GiB ở ba lần
  đo ổn định, lần cuối giảm khoảng 796 MiB. Không có thay đổi code nên không cần
  chạy unit/build tests; các kiểm tra vận hành trên là bằng chứng cho yêu cầu này.

## Known Issues

- RAM host thay đổi theo tiến trình khác; chênh lệch trước/sau không phải phép đo
  riêng tuyệt đối của project. Docker stats riêng cho thấy khoảng 759 MiB trước dừng.
- Worker kết thúc với exit 137 sau timeout 30 giây; khi bật lại nên kiểm tra cơ chế
  phục hồi job nếu có job đang xử lý. PostgreSQL dừng với exit 0.
- Autostart vẫn enabled nên project có thể chạy lại ở lần đăng nhập/boot tiếp theo.

## Next Best Action

- Giữ project tắt theo yêu cầu thử RAM hiện tại.
- Khi người dùng muốn bật lại, chạy
  `systemctl --user start business-ai-agents.service`, rồi kiểm tra health và worker.
