# Session: Kiểm tra frontend Docker cổng 13000

## Context

- User request: kiểm tra project có đúng đang dùng image Docker chạy frontend ở cổng
  13000 hay không.
- Agent: Claude Code; ngày 2026-10-12, khoảng 09:00 UTC+7. Chỉ đọc, không sửa code.

## Files Changed

- Chỉ AI_LOGS: `HANDOFF.md`, `TASKS.md` và session này.

## Findings

- `docker ps`: `businessaiagents-frontend-1`, image `businessaiagents-frontend`
  (ID `380c9413d7d0`, build 2026-09-04 từ `apps/web/Dockerfile`, base `node:22-alpine`),
  `Up (healthy)`, ports `0.0.0.0:13000->3000/tcp` và `[::]:13000->3000/tcp`.
- Compose labels: config `docker-compose.yml` + `docker-compose.multi-user.yml`.
  `docker-compose.yml` mặc định `${FRONTEND_PORT:-3000}:3000`; cổng 13000 đến từ
  `scripts/start_local_autostart.sh` (`FRONTEND_PORT=13000`, `--no-build`), được
  systemd user `business-ai-agents.service` (enabled/active) gọi.
- CMD thực tế là override multi-user: `npm run build` rồi
  `node .next/standalone/server.js`, `NODE_ENV=production`; tiến trình trong container
  `next-server (v15.5.23)`. CMD `npm run dev` trong Dockerfile bị ghi đè.
- Mounts: bind `apps/web` → `/app`, named volumes `frontend_modules`, `frontend_next`.
  Image chỉ cung cấp runtime Node; code là source host tại thời điểm container start.
- Cổng 13000 trên host chỉ có `docker-proxy` lắng nghe, không có Next.js chạy ngoài Docker.

## Commands / Tests Run

- `docker ps -a`, `docker images`, `docker inspect businessaiagents-frontend-1`,
  `docker image inspect businessaiagents-frontend`, `docker top`, `ss -ltnp`, `ps`.
- `systemctl --user is-enabled/is-active business-ai-agents.service` — enabled/active.
- `curl http://localhost:13000{/,/chat,/api/v1/health}` — 200/200/200.

## Next

- Không có việc kỹ thuật mới. Sau khi sửa frontend cần `docker restart
  businessaiagents-frontend-1` để build lại trong container.
