#!/bin/sh
# A named node_modules volume can outlive both the image and a lockfile security update.
set -eu

fingerprint=$(
  { cat package.json package-lock.json; node -p 'process.versions.modules + ":" + process.platform + ":" + process.arch'; } |
    sha256sum | cut -d ' ' -f 1
)
marker=node_modules/.dependency-fingerprint
installed=$(cat "$marker" 2>/dev/null || true)
if [ "$fingerprint" != "$installed" ] || ! npm ls --include=dev --all >/dev/null 2>&1; then
  npm ci --include=dev --no-audit --no-fund
  printf '%s\n' "$fingerprint" > "$marker"
fi
