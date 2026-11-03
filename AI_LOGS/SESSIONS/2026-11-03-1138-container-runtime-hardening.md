# Session: Tiếp tục backlog — container API/worker không đặc quyền

## Context

- User request: sau khi đọc AI_LOGS, "vậy bạn tiếp tục công việc cho tôi đi đc k".
- Agent: Codex. Date: 2026-11-03, Asia/Bangkok.
- Chọn phần kỹ thuật đã được duyệt tại DEC-064: container non-root và mã chỉ đọc; không đụng
  các bước cần chủ sở hữu đăng nhập hoặc chọn cấu hình triển khai.
- Harness bootstrap thành công; intake #15 high-risk, `US-CONTAINER-RUNTIME-HARDENING`,
  DEC-066 / decision 0053. Ban đầu working tree sạch; nhánh ahead 46 theo origin ref cục bộ.

## Files Changed

- `apps/api/Dockerfile`: tách dependency/runtime, tạo USER 10001, storage dir và môi trường tmp.
- `apps/api/app/prepare_storage.py`, `apps/api/tests/test_prepare_storage.py`: chuẩn bị quyền
  bằng directory descriptors/nofollow; giữ nội dung/mode; kiểm tra idempotence và symlink.
- `apps/api/app/services/latex_compiler.py`, `apps/api/tests/test_latex_compiler.py`: sử dụng
  cgroup PID/thread bound thay nproc theo host UID khi ranh giới hữu hạn được thực thi.
- `docker-compose.yml`, `docker-compose.team.yml`: init volume cô lập, source/root chỉ đọc,
  zero capabilities/no-new-privileges, tmpfs, UID/GID, PID/thread limits, init dependency.
- `scripts/verify_container_hardening.sh`: cấu hình ba chế độ; volume/DB tổng hợp cô lập;
  storage/restore/secret-permission fixture, symlink, OCR/LaTeX với 40 luồng phụ, tùy chọn live.
- `README.md`, `Docs/Team Deployment Runbook.md`: vận hành, quyền file-mounted secret, restore,
  kiểm thử và tái sử dụng dependency image khi đĩa hạn chế.
- `docs/decisions/0053-unprivileged-container-runtime.md` và bốn tệp story
  `docs/stories/container-runtime-hardening/{overview,design,execplan,validation}.md`.
- `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`, session này.

## Work Done / Decisions

- API/worker hiện chạy UID/GID 10001:10001, root filesystem và `/app` chỉ đọc; chỉ named volume
  tài liệu và `/tmp` tmpfs 512 MiB có quyền ghi. PID/thread limit 256, zero capabilities,
  no-new-privileges. Init root limit 64 chỉ có CHOWN/DAC_OVERRIDE, không mạng/env/secret, một volume.
- Init đổi ownership cần thiết trong volume; không chmod hoặc đổi byte, không theo symlink.
- Giữ nguyên đăng nhập, các cờ tính năng, provider AI và schema. Không gọi AI thật.
- Build chuẩn tải base Python mới và bắt đầu cài TeX/OCR rất lớn; đã dừng sớm (exit 130) khi
  `/` còn ~3,5 GB. Không xóa tài nguyên để lấy chỗ. Tách stage cho phép runtime build dựa trên
  ảnh root trước phiên; hash uv.lock source/image trùng, pip check sạch. Build runtime thành công.
- Sau chuyển đổi đầu tiên, LaTeX lỗi vì `--nproc=32` tính mọi luồng cùng host UID (72 luồng),
  khiến XeTeX không tạo được xdvipdfmx. Bổ sung cgroup limit thực thi theo container, dùng ranh
  giới đó khi ≤256; giữ nproc cũ ngoài cgroup hữu hạn. CPU/memory/file/timeout/no-shell-escape
  giữ nguyên. Canary 40 luồng phụ tái hiện và kiểm chứng sửa lỗi.
- Backup trước đổi quyền: DB custom dump, object archive, snapshot hash DB/tệp và cấu hình
  rollback tại `~/business-ai-agents-backups/20261103-1135-before-container-hardening/` (riêng tư).
  Giữ ảnh `businessaiagents-api:pre-hardening-20261103` và worker tương ứng. Không sửa `.env`.
- Chỉ API/worker được recreate, thêm init đã thoát 0; 20 container khác giữ nguyên ID.

## Commands / Tests Run

```text
scripts/bootstrap-harness.sh
scripts/bin/harness-cli query matrix --active --summary
cd apps/api && uv run --frozen python -m pytest -q
cd apps/api && uv run --frozen ruff check .
bash -n scripts/verify_container_hardening.sh
docker compose --progress plain build api worker                         # dừng sớm vì đĩa
docker compose --progress plain build --build-arg API_DEPENDENCIES_IMAGE=businessaiagents-api:pre-hardening-20261103 api worker
docker build --check apps/api
docker run --rm --pull never --network none --entrypoint python businessaiagents-api -m pip check
bash scripts/verify_container_hardening.sh
bash scripts/verify_container_hardening.sh --live
scripts/verify_local_autostart.sh
git diff --check
```

- Triển khai riêng API/worker: cùng Compose local multi-user và biến port như autostart,
  `up -d --no-build --wait --wait-timeout 180 api worker` sau sao lưu/dừng hai ứng dụng.
- Snapshot trước/sau dùng SQL row hashes của toàn bộ bảng và SHA-256/mode tệp, không in nội dung.
- HTTP smoke qua frontend: `/`, `/account`, `/chat`, `/research`, `/graph`, `/research/new`,
  `/api/v1/health`, `/api/v1/auth/config`; API health và `/api/v1/system/readiness`.
- POST LaTeX preview thật qua proxy: PDF cơ bản và fontspec/Noto Serif với văn bản tiếng Việt.
- Truy vấn chẩn đoán ban đầu dùng nhầm cột status của workspace và đường `/api/v1/readiness`;
  đã đối chiếu schema/OpenAPI, dùng đúng `processing_status` và `/api/v1/system/readiness`.

## Verification Result

- API **582/582** (12 case mới), Ruff/shell syntax/Dockerfile check sạch.
- Cấu hình local/multi-user/team; canary trên ảnh và hai container thật: đạt. Chứng minh UID,
  zero capabilities/no-new-privileges, source/root không ghi được, PID limit, volume private files,
  idempotence, symlink isolation, group-readable fixture, storage/restore, OCR, XeLaTeX: đạt.
- PostgreSQL tạm: toàn bộ migration tới `7d9f1b3c5e68`; `alembic check` không drift.
- Sau kiểm thử cuối: 46 bảng, **9250 hàng**, **4 tệp / 1100607 byte**; mọi hash/mode trước/sau khớp.
- Runtime health/readiness, 8 route frontend/proxy, PDF tiếng Việt và autostart đạt; log mới không
  có marker traceback/permission/readonly/critical. Các DB/network/volume thử đã dọn sạch.
- Không chạy browser E2E/frontend unit vì không đổi UI; số 84/84 E2E cũ thuộc phiên 27/10.
- `harness-cli story complete US-CONTAINER-RUNTIME-HARDENING` chạy proof mới và đạt; story đã
  implemented. Backlog #1 ghi việc đồng bộ tóm tắt bàn giao/trạng thái lịch sử; story tối ưu tổng
  thể và các bước nghiệm thu của chủ sở hữu vẫn giữ nguyên.
- Chưa chạy hết clean dependency build do đĩa; ảnh runtime đã build/kiểm chứng từ dependency có
  lockfile trùng. Không coi clean build bị dừng là đạt. Chưa commit hoặc push phiên này.

## Known Issues

- `/` còn khoảng 3,6 GB; không bắt đầu clean TeX/OCR/team build lớn khi chưa có chỗ.
- Chủ sở hữu vẫn cần tạo local owner, thử kết nối ChatGPT thật và lấy client ID web nếu chọn.
- Sandbox CLI và chuyển mã cầu nối ra ngoài repo còn tồn đọng; nghiên cứu sâu chưa bật;
  Gemini embedding chưa chuyển. Không đánh dấu toàn bộ optimization program hoàn tất.
- Một số mục lịch sử trong HANDOFF/TASKS và trạng thái Harness chưa phản ánh phiên mới nhất;
  đã sửa dòng "repo chỉ có 1 commit" trong TASKS, ưu tiên entry ngày mới nhất khi tiếp quản.
- FastAPI TestClient còn warning deprecation có từ trước; không làm test thất bại.

## Next Best Action

- Tiếp tục S7/S9: sandbox CLI và cài cầu nối ngoài cây mã, giữ provider/auth hiện tại.
- Khi chủ sở hữu thao tác được, thử ChatGPT tại `http://localhost:13000/account` trên máy chủ.
- Rà soát thay đổi phiên này trước commit/push; không xóa backup/ảnh rollback để lấy chỗ.
