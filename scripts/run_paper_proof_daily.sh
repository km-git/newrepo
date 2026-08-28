#!/usr/bin/env bash
# LLM-free daily paper proof: resolve outcomes → OHLC paper sim → 30-day ledger.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
LOG_DIR="${EW_PAPER_PROOF_LOG_DIR:-output/autonomous/paper_proof}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/run_${STAMP}.log"
mkdir -p "$LOG_DIR"

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

# Disable all LLM / AI model spend
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

# Execution policy (from merged ultimate trading system)
export EW_BLOCKED_TFS="${EW_BLOCKED_TFS:-1d,12h}"
export EW_DIRECTION_GATES="${EW_DIRECTION_GATES:-1}"
export EW_REGIME_GATES="${EW_REGIME_GATES:-1}"
export EW_TP1_EXIT_PCT="${EW_TP1_EXIT_PCT:-50}"
export EW_BREAKEVEN_AFTER_TP1="${EW_BREAKEVEN_AFTER_TP1:-1}"
export EW_PROBE_MAX_LEGS="${EW_PROBE_MAX_LEGS:-2}"
export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_PAPER_MAX_POSITIONS="${EW_PAPER_MAX_POSITIONS:-5}"

exec > >(tee -a "$LOG") 2>&1
echo "[paper-proof] started $(date -u +%Y-%m-%dT%H:%M:%SZ) log=$LOG"

echo "=== Phase 1: paper forward tick (no LLM) ==="
"$PY" ew_tool.py --paper-forward

echo "=== Phase 2: effectiveness audit with paper gate ==="
EW_EFFECTIVENESS_PAPER=1 "$PY" ew_tool.py --effectiveness-audit --effectiveness-paper

echo "[paper-proof] complete $(date -u +%Y-%m-%dT%H:%M:%SZ)"
