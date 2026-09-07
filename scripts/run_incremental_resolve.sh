#!/usr/bin/env bash
# Mid-day incremental resolve: only setups not checked in EW_RESOLVE_RECHECK_HOURS (default 6h).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_OHLC_PARALLEL="${EW_OHLC_PARALLEL:-1}"
export EW_OHLC_PARALLEL_WORKERS="${EW_OHLC_PARALLEL_WORKERS:-8}"
export EW_PAPER_FORWARD_SKIP_RESOLVE=0
export EW_RESOLVE_MODE=incremental
export EW_RESOLVE_RECHECK_HOURS="${EW_RESOLVE_RECHECK_HOURS:-6}"
export EW_RESOLVE_VERBOSE="${EW_RESOLVE_VERBOSE:-1}"

echo "[incremental-resolve] started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PY" -c "
import json
from engine.outcome_tracker import run_learning_phase
print(json.dumps(run_learning_phase(is_crypto=True, resolve_mode='incremental'), indent=2, default=str))
"
echo "[incremental-resolve] complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
