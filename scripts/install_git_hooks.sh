#!/usr/bin/env bash
# Enable repo git hooks for proof gates (step 7 in agent harness setup).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

chmod +x .githooks/pre-commit .githooks/pre-push 2>/dev/null || true

git config core.hooksPath .githooks
echo "[install-git-hooks] core.hooksPath=.githooks"
echo "[install-git-hooks] pre-commit → scripts/hooks/run_proof_gate.sh fast (on staged paper/execution)"
echo "[install-git-hooks] skip once: EW_SKIP_PROOF_HOOKS=1"
