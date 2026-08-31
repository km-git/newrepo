#!/usr/bin/env bash
# LLM-free daily trading ops: proof + GOAT + tactical + health readiness.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
LOG_DIR="${EW_DAILY_OPS_LOG_DIR:-output/autonomous/daily_ops}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/run_${STAMP}.log"
mkdir -p "$LOG_DIR"

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

export EW_IMPROVEMENT_LLM=0
export EW_AI_IMPROVEMENT=0
export EW_DEEP_RESEARCH=0
export EW_BRAIN_SELF_IMPROVE=0
export EW_BRAIN_CONSENSUS=0
export EW_SOCIAL_VALIDATION=0
export EW_PR_LLM_ADVISORY=0
export EW_PR_AUTO_MERGE=0
export EW_EXECUTION_CONSENSUS_LLM=0
export EW_LLM_EW_BYPASS=1
export EW_BLOCKED_TFS="${EW_BLOCKED_TFS:-1d,12h}"
export EW_DIRECTION_GATES="${EW_DIRECTION_GATES:-1}"
export EW_REGIME_GATES="${EW_REGIME_GATES:-1}"
export EW_TP1_EXIT_PCT="${EW_TP1_EXIT_PCT:-50}"
export EW_ALWAYS_SMART_RISK=1
export EW_DYNAMIC_RISK=1
export EW_TACTICAL_SAFEGUARD=1
export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_PAPER_FORWARD_SKIP_RESOLVE="${EW_PAPER_FORWARD_SKIP_RESOLVE:-1}"
export EW_RESOLVE_MODE="${EW_RESOLVE_MODE:-skip}"
export EW_OHLC_PARALLEL="${EW_OHLC_PARALLEL:-1}"
export EW_OHLC_PARALLEL_WORKERS="${EW_OHLC_PARALLEL_WORKERS:-8}"

POLICY="${ROOT}/config/profit_lab_policy.env"
if [[ -f "$POLICY" ]] && [[ "${EW_USE_PROFIT_LAB_POLICY:-1}" != "0" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$POLICY"
  set +a
  echo "[daily-ops] loaded profit lab policy from $POLICY"
fi

exec > >(tee -a "$LOG") 2>&1
echo "[daily-ops] started $(date -u +%Y-%m-%dT%H:%M:%SZ) log=$LOG"
echo "[daily-ops] resolve_mode=${EW_RESOLVE_MODE} skip_resolve=${EW_PAPER_FORWARD_SKIP_RESOLVE}"
"$PY" ew_tool.py --daily-trading-tick --daily-trading-tick-resolve skip "$@"
echo "[daily-ops] complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
