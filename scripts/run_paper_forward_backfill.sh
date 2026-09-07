#!/usr/bin/env bash
# Backfill the 30-day paper-forward proof window with point-in-time OHLC replay.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

export EW_IMPROVEMENT_LLM=0
export EW_AI_IMPROVEMENT=0
export EW_DEEP_RESEARCH=0
export EW_GATEWAY_QUIET=1
export EW_FETCH_QUIET=1
export EW_PAPER_FORWARD_SKIP_RESOLVE=1
export EW_PAPER_MAX_POSITIONS="${EW_PAPER_MAX_POSITIONS:-5}"
export EW_BLOCKED_TFS="${EW_BLOCKED_TFS:-1d,12h}"
export EW_ALWAYS_SMART_RISK=1

FORCE="${EW_PAPER_BACKFILL_FORCE:-0}"
ARGS=(--paper-forward-backfill)
if [[ "$FORCE" == "1" ]]; then
  ARGS+=(--paper-forward-backfill-force)
fi
if [[ -n "${EW_PAPER_PROOF_DAYS:-}" ]]; then
  ARGS+=(--paper-forward-days "$EW_PAPER_PROOF_DAYS")
fi

echo "[paper-backfill] started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PY" ew_tool.py "${ARGS[@]}"
echo "[paper-backfill] complete — see reports/PAPER_FORWARD.md"
