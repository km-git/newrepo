#!/usr/bin/env bash
# Apply optimized profit-lab policy, run forward proof + profit lab on filtered history.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

# Load optimized policy
set -a
# shellcheck disable=SC1091
source "${ROOT}/config/profit_lab_policy.env"
set +a

export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_IMPROVEMENT_LLM=0
export EW_AI_IMPROVEMENT=0
export EW_PAPER_FORWARD_SKIP_RESOLVE="${EW_PAPER_FORWARD_SKIP_RESOLVE:-1}"
export EW_PROFIT_LAB_SWEEP=0

echo "[policy-forward] policy: BLOCK_TFS=${EW_BLOCKED_TFS} BLOCK_DIRS=${EW_BLOCKED_DIRECTIONS} MIN_STOP=${EW_MIN_STOP_PCT}"
echo "[policy-forward] started $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "=== Phase 1: profit lab (policy-filtered history) ==="
"$PY" ew_tool.py --profit-lab

echo "=== Phase 2: paper forward tick (gated) ==="
"$PY" ew_tool.py --paper-forward

echo "=== Phase 3: daily ops composite ==="
EW_PROFIT_LAB=1 "$PY" ew_tool.py --daily-trading-tick

echo "[policy-forward] complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
