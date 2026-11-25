# Overview

## Current Behavior

Audit phát hiện writer có thể đổi nghĩa claim đã xác minh; backup thủ công không quiesce mặc định;
local model có khoảng trống che khóa/timeout/cấu hình/UI; dependency volume có thể bỏ qua lockfile;
CI thiếu kiểm tra PostgreSQL và usage/eval bỏ sót chi phí thất bại.

## Target Behavior

- Báo cáo không biến câu đã xác minh thành khẳng định mới mà vẫn nhận citation hợp lệ.
- Backup thủ công dùng cùng ranh giới nhất quán và retention có nhận dạng với backup định kỳ.
- Không trả credential qua JSON/catalogue/tool arguments; deadline bao gồm header và body.
- Team runbook và UI kết nối local nhất quán; lockfile được áp dụng khi khởi động frontend.
- Bản vá Next 15 và dev dependency tương thích; CI kiểm lockfile và migration PostgreSQL.
- Usage bao gồm mọi attempt có số đo; eval thể hiện failures, manifest và điều kiện so sánh.
- Có bằng chứng Mistral inference/embedding thực tế, không đổi mặc định để thử.

## Affected Docs

`Docs/Research System Implementation Plan.md`, `Docs/Team Deployment Runbook.md`,
`Docs/Local Model Deployment Plan.md`, README và các story optimization/deployed-local-models.
