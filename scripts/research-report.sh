#!/usr/bin/env bash
# Chạy một lượt nghiên cứu sâu qua API, theo dõi tiến độ và lưu báo cáo Markdown có trích dẫn.
#   scripts/research-report.sh "Câu hỏi nghiên cứu"
# Biến môi trường:
#   RESEARCH_API_URL    mặc định http://localhost:13000/api/v1 (chế độ nhóm: https://<tên-miền>/api/v1)
#   RESEARCH_API_TOKEN  token tài khoản dịch vụ có scope research:run + research:read (chế độ nhóm)
#   RESEARCH_OUTPUT_DIR mặc định ./research-reports (đã gitignore)
#   RESEARCH_TIMEOUT    số giây chờ tối đa, mặc định 1200
set -euo pipefail

question=${1:-}
[[ ${#question} -ge 10 ]] || { echo "Cần câu hỏi ít nhất 10 ký tự." >&2; exit 2; }
api=${RESEARCH_API_URL:-http://localhost:13000/api/v1}
out_dir=${RESEARCH_OUTPUT_DIR:-research-reports}
timeout=${RESEARCH_TIMEOUT:-1200}
auth=()
[[ -n "${RESEARCH_API_TOKEN:-}" ]] && auth=(-H "Authorization: Bearer ${RESEARCH_API_TOKEN}")

json_field() { python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1]) if not isinstance(d.get(sys.argv[1]), dict) else json.dumps(d[sys.argv[1]]))' "$1"; }

body=$(python3 -c 'import json,sys; print(json.dumps({"question": sys.argv[1]}))' "$question")
response=$(curl -sS -w '\n%{http_code}' "${auth[@]}" -H 'Content-Type: application/json' -d "$body" "$api/research-runs")
status=${response##*$'\n'}
payload=${response%$'\n'*}
if [[ "$status" != "202" ]]; then
  echo "Không bắt đầu được (HTTP $status): $payload" >&2
  exit 1
fi
run_id=$(json_field id <<<"$payload")
web_url="${api%/api/v1}/research/runs/$run_id"
echo "Đã xếp hàng lượt $run_id — theo dõi: $web_url"

deadline=$((SECONDS + timeout))
last_stage=""
while (( SECONDS < deadline )); do
  detail=$(curl -sS "${auth[@]}" "$api/research-runs/$run_id")
  state=$(json_field status <<<"$detail")
  stage=$(json_field stage <<<"$detail")
  if [[ "$stage" != "$last_stage" ]]; then echo "  • $stage ($state)"; last_stage=$stage; fi
  case "$state" in
    completed) break ;;
    failed|cancelled)
      echo "Lượt nghiên cứu $state: $(json_field error_message <<<"$detail")" >&2
      exit 1 ;;
  esac
  sleep 10
done
[[ "$state" == "completed" ]] || { echo "Hết thời gian chờ; xem tiến độ tại $web_url" >&2; exit 1; }

mkdir -p "$out_dir"
slug=$(python3 -c 'import re,sys,unicodedata; s=unicodedata.normalize("NFKD",sys.argv[1]).encode("ascii","ignore").decode().lower(); print(re.sub(r"[^a-z0-9]+","-",s).strip("-")[:60] or "report")' "$question")
file="$out_dir/$(date +%Y%m%d-%H%M)-$slug.md"
curl -sS "${auth[@]}" "$api/research-runs/$run_id/export.md" -o "$file"
metrics=$(json_field metrics <<<"$detail")
python3 - "$metrics" "$file" "$web_url" <<'PY'
import json, sys
m = json.loads(sys.argv[1])
cited, uncited = m.get("cited_sentences", 0), m.get("uncited_sentences", 0)
print(f"Đã lưu: {sys.argv[2]}")
print(f"Câu có trích dẫn: {cited}/{cited + uncited} · nguồn trích dẫn: {m.get('sources_cited', 0)}"
      f" · góc nhìn: {', '.join(m.get('perspectives_covered') or []) or 'không'}")
print(f"Lượt gọi AI: {m.get('llm_calls', 0)} · thời gian: {round(m.get('wall_time_ms', 0) / 1000)} giây")
print(f"Bản nháp cần duyệt: {sys.argv[3]}")
PY
