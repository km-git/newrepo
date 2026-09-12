#!/usr/bin/env bash
# Optional ECC agent harness (steps 4–6). Installs to user home, not vendored into repo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Spec Kit (required for this repo)"
bash "$ROOT/scripts/setup_spec_kit.sh"

echo ""
echo "==> ECC plugin (optional — 278 skills + hooks)"
echo "ECC is installed per-developer, not committed to this repo."
echo ""
echo "In Cursor / Claude Code chat:"
echo "  /plugin marketplace add github.com/affaan-m/ecc"
echo "  /plugin install ecc@ecc"
echo ""
echo "Or clone and copy skills locally:"
echo "  git clone --depth 1 https://github.com/affaan-m/ecc.git /tmp/ecc"
echo "  mkdir -p ~/.cursor/skills"
echo "  cp -R /tmp/ecc/skills/* ~/.cursor/skills/"
echo ""
echo "Repo-specific skills (committed):"
echo "  .cursor/skills/speckit-*"
echo "  .cursor/skills/proof-first-trading"
echo ""
echo "==> Git proof hooks (recommended)"
bash "$ROOT/scripts/install_git_hooks.sh"
