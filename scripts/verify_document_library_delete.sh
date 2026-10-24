#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

(
  cd "$repo_root/apps/api"
  uv run ruff check app/services/documents.py app/api/documents.py app/schemas/documents.py \
    tests/test_documents.py tests/test_auth.py
  uv run pytest tests/test_documents.py tests/test_auth.py -q
)

(
  cd "$repo_root/apps/web"
  npm test -- --run app/documents/page.test.tsx lib/documents.test.ts
  npm run lint
  npm run build

  document_library_e2e_port="${DOCUMENT_LIBRARY_E2E_PORT:-3211}"
  npm run start -- -p "$document_library_e2e_port" >/tmp/document-library-e2e-server.log 2>&1 &
  document_library_e2e_pid=$!
  trap 'kill "$document_library_e2e_pid" 2>/dev/null || true' EXIT
  for _ in $(seq 1 30); do
    if curl --fail --silent "http://localhost:$document_library_e2e_port/documents" >/dev/null; then
      break
    fi
    sleep 1
  done
  E2E_BASE_URL="http://localhost:$document_library_e2e_port" \
    npx playwright test e2e/document-upload.spec.ts --grep "uploaded PDF opens"
  kill "$document_library_e2e_pid"
  wait "$document_library_e2e_pid" 2>/dev/null || true
  trap - EXIT
)
