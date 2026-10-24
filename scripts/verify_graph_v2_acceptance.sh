#!/usr/bin/env bash

set -u -o pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
checklist="$repo_root/Docs/Graph Intelligence v2 Product Acceptance Checklist.md"
api_base_url=${GV2_API_BASE_URL:-http://localhost:18000}
acceptance_status=0

if curl --fail --silent "$api_base_url/api/v1/health" >/dev/null \
  && curl --fail --silent "$api_base_url/api/v1/system/features" >/dev/null \
  && curl --fail --silent "$api_base_url/api/v1/system/readiness" >/dev/null; then
  echo "GV2_RUNTIME_OK"
else
  echo "GV2_RUNTIME_FAILED" >&2
  acceptance_status=1
fi

if (cd "$repo_root" && docker compose exec -T api python -m app.operations verify-graph >/dev/null); then
  echo "GV2_GRAPH_INVARIANTS_OK"
else
  echo "GV2_GRAPH_INVARIANTS_FAILED" >&2
  acceptance_status=1
fi

if (cd "$repo_root" && docker compose exec -T api python -m app.operations verify-chat-provider); then
  echo "GV2_CHAT_PROVIDER_ACCESS_OK"
else
  echo "GV2_CHAT_PROVIDER_ACCESS_PENDING" >&2
  acceptance_status=1
fi

walkthrough=$(
  awk '
    /^## Product-owner walkthrough/ { active = 1; next }
    /^## / && active { exit }
    active { print }
  ' "$checklist"
)
decision=$(
  awk '
    /^## Product-owner decision/ { active = 1; next }
    /^## / && active { exit }
    active { print }
  ' "$checklist"
)

if printf '%s\n' "$walkthrough" | rg --quiet '^- \[ \]'; then
  echo "GV2_WALKTHROUGH_PENDING" >&2
  acceptance_status=1
else
  echo "GV2_WALKTHROUGH_ACCEPTED"
fi

accepted_count=$(
  printf '%s\n' "$decision" \
    | rg --count '^- \[x\] (Accepted\.|Accepted with follow-up work\.)$' \
    || true
)
if [[ "$accepted_count" == "1" ]] \
  && ! printf '%s\n' "$decision" | rg --quiet '^- \[x\] Changes required\.$'; then
  echo "GV2_PRODUCT_DECISION_ACCEPTED"
else
  echo "GV2_PRODUCT_DECISION_PENDING" >&2
  acceptance_status=1
fi

if [[ "$acceptance_status" == "0" ]]; then
  echo "GRAPH_V2_ACCEPTANCE_OK"
fi
exit "$acceptance_status"
