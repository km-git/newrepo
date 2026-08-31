#!/usr/bin/env bash
# Profit laboratory — fee-adjusted expectancy, CPCV, quantstats, optional vectorbt sweep.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_EXPECTANCY_GATES=1
SWEEP="${EW_PROFIT_LAB_SWEEP:-0}"
if [[ "${1:-}" == "--sweep" ]]; then
  SWEEP=1
  shift
fi
ARGS=(--profit-lab)
if [[ "$SWEEP" == "1" ]]; then
  ARGS+=(--profit-lab-sweep)
fi
echo "[profit-lab] started $(date -u +%Y-%m-%dT%H:%M:%SZ) sweep=$SWEEP"
"$PY" ew_tool.py "${ARGS[@]}" "$@"
echo "[profit-lab] complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
