#!/usr/bin/env bash
# One-shot bootstrap: venv, pip deps, GitHub libs, token savers, gh CLI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"

echo "==> Creating venv (if needed)"
if [ ! -d ".venv/bin" ]; then
  "$PY" -m venv .venv
fi
export PATH="$ROOT/.venv/bin:$PATH"

echo "==> Running Python setup_environment"
"$ROOT/.venv/bin/python" -m engine.setup_environment "$@"

echo "==> Setup complete. Use: .venv/bin/python ew_tool.py --health"
