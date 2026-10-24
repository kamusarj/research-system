#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spec="$repo_root/Docs/Intake Occurrence and Receipt Specification.md"
completion="$repo_root/Docs/Research System Completion Plan.md"
architecture="$repo_root/Docs/Research System Architecture Design.md"
pipeline="$repo_root/Docs/Source Processing Pipeline.md"
decision="$repo_root/docs/decisions/0015-source-neutral-intake-receipts.md"

required_patterns=(
  "## 3. Terminology and Invariants"
  '### 4.1. `IntakeReceipt`'
  '### 4.2. `IntakeReceiptItem`'
  "Discord uses its message ID"
  "different source occurrence"
  "multiple URL and document items"
  "durably stored before"
  "SOURCE_OCCURRENCE_CONFLICT"
  "SOURCE_ITEM_CONFLICT"
  "initial_disposition"
  "partial unique"
  "## 6. Authorization, Privacy, and Audit"
  "## 7. Concurrency and Transaction Rules"
  "## 8. Additive Migration and Rollout"
  "## 9. Validation Contract"
  "## 10. Gate D Entry Criteria"
)

for pattern in "${required_patterns[@]}"; do
  rg --fixed-strings --quiet "$pattern" "$spec"
done

for file in "$spec" "$completion" "$architecture" "$pipeline" "$decision"; do
  test -s "$file"
  fence_count="$(rg --count '^```' "$file" || true)"
  if (( fence_count % 2 != 0 )); then
    echo "Unbalanced Markdown fences: $file" >&2
    exit 1
  fi
done

rg --fixed-strings --quiet "Intake Occurrence and Receipt Specification.md" "$completion"
rg --fixed-strings --quiet "IntakeReceipt" "$architecture"
rg --fixed-strings --quiet "receipt item" "$pipeline"
rg --fixed-strings --quiet "Do not implement Discord" \
  "$repo_root/docs/stories/intake-receipts-spec/overview.md"

git -C "$repo_root" diff --check -- \
  "Docs/Intake Occurrence and Receipt Specification.md" \
  "Docs/Research System Completion Plan.md" \
  "Docs/Research System Architecture Design.md" \
  "Docs/Source Processing Pipeline.md" \
  "docs/stories/intake-receipts-spec" \
  "docs/decisions/0015-source-neutral-intake-receipts.md" \
  "scripts/verify_intake_receipt_spec.sh"

echo "INTAKE_RECEIPT_SPEC_OK"
