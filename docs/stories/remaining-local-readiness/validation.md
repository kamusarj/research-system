# Validation

## Proof Strategy

Test nhỏ cho từng phần, sau đó kiểm tra tổng hợp. Không dùng credential thật làm fixture.

| Layer | Proof |
| --- | --- |
| Unit | Keyring path/session/attributes deny; Codex tool flags; research token/context contracts |
| Integration | Keyring broker, synthetic CLI completion, login/CSRF, backup/restore |
| Platform | Installed bridge path/mode, timer, restricted sandbox, runtime health |
| UI | Web unit/type/lint/build; mobile Lighthouse trước/sau và browser smoke |

## Results

2026-11-03, local production 13000/18000 và stack browser cô lập riêng:

| Layer | Result |
| --- | --- |
| API | Full suite 603 test; bridge/policy 38; research targeted 35; backup retention/failure 4 |
| Web | 205 unit test, typecheck/lint và production build đạt; `/chat`146kB first load |
| CLI | Codex/agy completion thật đạt; canary Codex không đọc được secret giả và không native tool event; broker negative read/mixed/session/write đạt |
| Auth | Owner tạo qua stdin; private credential0600 ngoài repo; anonymous401, owner200, thiếu CSRF403 |
| Browser | Owner/viewer6 case + SSR/timezone/history3 case đạt; auth fixture hoàn toàn tổng hợp |
| Performance | Authenticated mobile80→91/91/92, median91; A11y 98; LCP khoảng3,3s, TBT33–37ms |
| Research | Native verifier40/40 verdict đúng, token−54,7%; replay8 run giảm0,88% chars; q2 thật completed/draft,18 câu có citation/9 nguồn |
| Backup | Timer 02:30 active/Linger=yes, chạy thử success; restore46 bảng và mọi tệp/hash khớp trong fixture riêng |
| Runtime | Container config/canary + live API/worker non-root/read-only/caps/storage/OCR/LaTeX/migration đạt |
| Dependencies | pypdf6.21.4 runtime, pip-audit API/Discord0; npm prod0, dev14 Moderate/0 High/Critical |
| Secrets | Gitleaks47 commit trước commit mới0; hook quét staged khi commit |

E2E tổng hợp cuối đạt81/81 case auth-disabled (9 auth skip có chủ ý); auth riêng 9/9 đạt. Tổng90 case đều được chạy trong đúng chế độ tương ứng. Các vòng trước có một timeout
document editor 30s rồi rerun 3/3 đạt, một timeout chờ history 5s rồi repeat 9/9 đạt. Test history nay
đợi response fixture trước khi kiểm DOM. Không sửa app hoặc tăng timeout toàn suite để che lỗi.

## Commands / Evidence

```bash
bash scripts/verify_local_readiness.sh
bash scripts/verify_container_hardening.sh --live
python3 scripts/verify_cli_isolation.py --codex-canary
systemctl --user start business-ai-agents-backup.service
E2E_BASE_URL=http://localhost:23000 npm run test:e2e
```

E2E chạy từ `apps/web`, backend 28000/Next 23000, project `baa-readiness-e2e`, PG tmpfs và object
volume riêng. API key fixture không dùng được, CLI/OAuth tắt; không gửi test mutation vào DB thật.
Auth lượt riêng có owner/viewer fixture và24 message tạo trực tiếp trong DB tạm; `E2E_CHAT_HISTORY=1`
chỉ bật ca đó khi đã seed. Timezone Pacific/Honolulu khác UTC của server, bắt hydration mismatch.

Lighthouse dùng Chrome thực + Lighthouse có sẵn trong npm tool cache, cookie chỉ được gắn vào
context localhost qua Playwright. Chỉ lưu metric JSON, không lưu raw HTML/cookie trong repo.
Chi tiết số đo: `docs/evaluations/local-readiness/README.md`. Các probe/restore command riêng
và kết quả ở session log; mechanical story proof không tự gọi provider tiêu quota.

## Limits / External Inputs

- Chưa chứng minh mục giảm20% token toàn pipeline8 câu; không dùng verifier benchmark thay thế.
- OpenAI key invalid, Gemini key thiếu, Claude probe có chỉ dấu billing, Ollama0 model.
- User chưa có domain; ChatGPT consent/client ID, offsite và product-owner acceptance chưa xong.
- Không force npm downgrade;14 Moderate dev/lint còn lại. Không ký thay user hoặc auto-publish.

## Final Mechanical Proof

`harness-cli story complete US-REMAINING-LOCAL-READINESS` đã chạy mới toàn bộ
`bash scripts/verify_local_readiness.sh` và pass: lock/ruff/API603, web205/lint/typecheck/build,
bash syntax và diff check. Story implemented, bốn proof flags đạt. Full E2E81/81 + auth9/9,
fixture và Next dev riêng đã gỡ. Bản backup cuối sau smoke success, API/worker resumed healthy.
Không còn việc triển khai local trong phạm vi story này. Các giới hạn/đầu vào ở trên vẫn giữ nguyên.

Pre-commit phát hiện3 false positive: public rollback image tag (2 chỗ) và password Compose
config fixture. Allowlist chỉ đúng image literal đã kiểm chứng, fixture đổi thành chuỗi test ngắn;
không bypass hook. Platform script được chạy lại sau thay đổi fixture.
