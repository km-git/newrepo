#!/usr/bin/env bash
# Weekly full outcome resolve + paper forward proof (batched parallel OHLC).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
LOG_DIR="${EW_WEEKLY_RESOLVE_LOG_DIR:-output/autonomous/weekly_resolve}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/run_${STAMP}.log"
mkdir -p "$LOG_DIR"

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_OHLC_PARALLEL="${EW_OHLC_PARALLEL:-1}"
export EW_OHLC_PARALLEL_WORKERS="${EW_OHLC_PARALLEL_WORKERS:-8}"
export EW_PAPER_FORWARD_SKIP_RESOLVE=0
export EW_RESOLVE_MODE=full
export EW_RESOLVE_RECHECK_HOURS=0
export EW_RESOLVE_VERBOSE="${EW_RESOLVE_VERBOSE:-1}"

exec > >(tee -a "$LOG") 2>&1
echo "[weekly-resolve] started $(date -u +%Y-%m-%dT%H:%M:%SZ) log=$LOG"
"$PY" ew_tool.py --daily-trading-tick --daily-trading-tick-resolve full --daily-trading-tick-fetch
echo "[weekly-resolve] complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
