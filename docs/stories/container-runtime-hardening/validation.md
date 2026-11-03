# Validation

## Proof Strategy

Kiểm tra cấu hình, quyền thực tế và chức năng đọc/ghi trước khi thay runtime. Không gọi AI thật.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Init bảo toàn nội dung/mode, idempotence, bỏ qua symlink, từ chối root symlink/missing |
| Integration | Volume root-owned/private files → UID 10001, không đổi đích symlink, storage roundtrip |
| Platform | Compose local/multi-user/team, non-root, root/source chỉ đọc, không capabilities/nâng quyền |
| Functional | OCR, XeLaTeX, Alembic trên PostgreSQL tạm, runtime health/readiness |
| Preservation | Sao lưu hợp lệ; SHA-256 tệp và số bản ghi trước/sau khớp |

Không chạy E2E trình duyệt vì không đổi UI; HTTP qua proxy frontend và canary runtime là bằng
chứng integration/platform. Bộ 84 browser E2E của phiên 27/10 là lịch sử, không tính lại cho phiên này.

## Fixtures

DB và volume cô lập; văn bản/ảnh tổng hợp, không credentials hoặc dữ liệu nghiên cứu thật.

## Commands

```bash
cd apps/api && uv run --frozen python -m pytest -q && uv run --frozen ruff check .
bash scripts/verify_container_hardening.sh
bash scripts/verify_container_hardening.sh --live
scripts/verify_local_autostart.sh
```

## Acceptance Evidence

2026-11-03:

- API 582/582 (12 case mới); Ruff sạch, shell syntax và `git diff --check` sạch.
- Local/multi-user/team config, root-owned volume/private files, symlink isolation, idempotence,
  group-readable fixture và restore tar root-owned bằng UID ứng dụng: đạt.
- Ảnh mới + hai container thật: UID/GID 10001, zero capabilities, no-new-privileges,
  root/source không ghi được, cgroup 256, storage roundtrip, LaTeX với 40 luồng phụ và OCR: đạt.
- Fresh PostgreSQL tạm: toàn bộ Alembic upgrade tới `7d9f1b3c5e68` và `alembic check` đạt.
- 8 route frontend/proxy + API health/readiness + HTTP LaTeX PDF (cả fontspec/Noto Serif tiếng Việt): đạt.
- Autostart verification đạt; 20 container khác giữ nguyên ID; API/worker không có dấu lỗi mới.
- Snapshot toàn bộ hàng của 46 bảng (9250 hàng) và 4 tệp (1100607 byte), hash/mode trước và sau khớp.
- Backup PostgreSQL/tệp đã kiểm tra trong `~/business-ai-agents-backups/20261103-1135-before-container-hardening/`.
- `pip check` sạch, hash uv.lock trong dependency image trùng source; `docker build --check` sạch.
  Clean dependency build dừng sớm vì ổ `/` còn 3,5–3,6 GB; runtime build thành công từ ảnh root
  đã kiểm chứng (không xóa image/cache/volume để lấy chỗ). Các fixture volume/network/DB đã gỡ.
