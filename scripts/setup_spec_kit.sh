#!/usr/bin/env bash
# Bootstrap Spec Kit via uv (steps 1–3). Safe to re-run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing uv (if missing)"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck disable=SC1091
  [[ -f "$HOME/.local/bin/env" ]] && source "$HOME/.local/bin/env"
fi

export PATH="${HOME}/.local/bin:${PATH}"

echo "==> Installing specify-cli from github/spec-kit"
uv tool install specify-cli --from git+https://github.com/github/spec-kit --force

if command -v specify >/dev/null 2>&1; then
  specify --version || true
else
  echo "WARN: specify not on PATH — add ~/.local/bin to PATH" >&2
fi

if [[ -d "$ROOT/.specify" ]]; then
  echo "==> Spec Kit already initialized at $ROOT/.specify"
  echo "    Skills: .cursor/skills/speckit-*"
  echo "    Flow: /speckit-constitution → /speckit-specify → /speckit-plan → /speckit-tasks → /speckit-implement"
else
  echo "==> Initializing Spec Kit (cursor-agent integration)"
  specify init --here --force --integration cursor-agent --ignore-agent-tools
fi

echo "==> Optional: enable git proof hooks"
echo "    bash scripts/install_git_hooks.sh"
