#!/usr/bin/env bash
# Install GitHub CLI (gh) for PR executive consensus and improvement workflows.
set -euo pipefail

if command -v gh >/dev/null 2>&1; then
  echo "gh already installed: $(command -v gh)"
  gh --version
  exit 0
fi

if [ -x /exec-daemon/gh ]; then
  ln -sf /exec-daemon/gh /usr/local/bin/gh 2>/dev/null || true
  if command -v gh >/dev/null 2>&1; then
    gh --version
    exit 0
  fi
fi

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$ARCH" in
  x86_64) GH_ARCH="amd64" ;;
  aarch64|arm64) GH_ARCH="arm64" ;;
  *) echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

if [ "$OS" = "linux" ]; then
  GH_VERSION="${GH_VERSION:-2.63.2}"
  TARBALL="gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz"
  URL="https://github.com/cli/cli/releases/download/v${GH_VERSION}/${TARBALL}"
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT

  echo "Downloading $URL"
  curl -fsSL "$URL" -o "$TMP/$TARBALL"
  tar -xzf "$TMP/$TARBALL" -C "$TMP"
  install -m 0755 "$TMP/gh_${GH_VERSION}_linux_${GH_ARCH}/bin/gh" /usr/local/bin/gh
  gh --version
  exit 0
fi

if [ "$OS" = "darwin" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew install gh
    gh --version
    exit 0
  fi
fi

echo "Could not auto-install gh on $OS/$ARCH — install manually: https://cli.github.com/"
exit 1
