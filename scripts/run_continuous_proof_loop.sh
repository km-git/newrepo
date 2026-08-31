#!/usr/bin/env bash
# Continuous proof loop: learn outcomes → refresh paper policy → paper-forward tick.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
LOG_DIR="${EW_CONTINUOUS_PROOF_LOG_DIR:-output/autonomous/continuous_proof}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/run_${STAMP}.log"
mkdir -p "$LOG_DIR"

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

export EW_IMPROVEMENT_LLM=0
export EW_AI_IMPROVEMENT=0
export EW_DEEP_RESEARCH=0
export EW_BRAIN_SELF_IMPROVE=0
export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_BLOCKED_TFS="${EW_BLOCKED_TFS:-1d,12h}"
export EW_DIRECTION_GATES="${EW_DIRECTION_GATES:-1}"
export EW_REGIME_GATES="${EW_REGIME_GATES:-1}"
export EW_ALWAYS_SMART_RISK=1
export EW_DYNAMIC_RISK=1
export EW_PAPER_MAX_POSITIONS="${EW_PAPER_MAX_POSITIONS:-5}"
export EW_PAPER_RELAX_GATES="${EW_PAPER_RELAX_GATES:-1}"
export EW_PAPER_REQUIRE_KILL_ZONE="${EW_PAPER_REQUIRE_KILL_ZONE:-0}"

exec > >(tee -a "$LOG") 2>&1
echo "[continuous-proof] started $(date -u +%Y-%m-%dT%H:%M:%SZ) log=$LOG"

"$PY" ew_tool.py --continuous-proof

echo "[continuous-proof] complete — see reports/CONTINUOUS_PROOF.md"
