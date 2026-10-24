#!/usr/bin/env bash
# Cài gitleaks (phiên bản ghim, kiểm SHA-256) vào scripts/bin/ và bật hook pre-commit quét secret.
# Chạy một lần sau khi clone: scripts/install-git-hooks.sh
set -euo pipefail

VERSION="8.30.1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/scripts/bin/gitleaks"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ASSET="linux_x64"; SHA="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb" ;;
  Linux-aarch64|Linux-arm64) ASSET="linux_arm64"; SHA="e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080" ;;
  Darwin-x86_64) ASSET="darwin_x64"; SHA="dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709" ;;
  Darwin-arm64) ASSET="darwin_arm64"; SHA="b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5" ;;
  *) echo "Nền tảng chưa hỗ trợ; tự cài gitleaks $VERSION vào PATH." >&2; ASSET="" ;;
esac

if [ -n "$ASSET" ] && ! { [ -x "$BIN" ] && "$BIN" version 2>/dev/null | grep -qx "$VERSION"; }; then
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  archive="gitleaks_${VERSION}_${ASSET}.tar.gz"
  curl -fsSL -o "$tmp/$archive" \
    "https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/${archive}"
  echo "$SHA  $tmp/$archive" | sha256sum -c - >/dev/null
  tar -xzf "$tmp/$archive" -C "$tmp" gitleaks
  mkdir -p "$(dirname "$BIN")"
  install -m 0755 "$tmp/gitleaks" "$BIN"
fi

git -C "$ROOT" config core.hooksPath .githooks
echo "Đã bật hook pre-commit quét secret (gitleaks $VERSION)."
