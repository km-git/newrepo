#!/usr/bin/env bash
# Continuous agent: monitor + hourly batch + paper P&L each cycle.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
export ACCOUNT_EQUITY="${ACCOUNT_EQUITY:-50000}"
export USDT_D_PCT="${USDT_D_PCT:-8.2}"
export EW_PAPER_AFTER_BATCH="${EW_PAPER_AFTER_BATCH:-1}"
export EW_PAPER_MAX_POSITIONS="${EW_PAPER_MAX_POSITIONS:-3}"

MONITOR_INTERVAL="${MONITOR_INTERVAL:-300}"
BATCH_INTERVAL="${BATCH_INTERVAL:-3600}"
BATCH_N="${BATCH_N:-50}"
LOG="${CONTINUOUS_LOG:-output/autodream/continuous_agent.log}"

mkdir -p "$(dirname "$LOG")"
echo "[continuous] started $(date -u +%Y-%m-%dT%H:%M:%SZ) equity=$ACCOUNT_EQUITY" | tee -a "$LOG"

while true; do
  echo "[continuous] tick $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
  python3 scripts/autodream_monitor.py \
    --once \
    --batch-interval "$BATCH_INTERVAL" \
    --batch-n "$BATCH_N" \
    2>&1 | tee -a "$LOG" || true

  python3 scripts/run_paper_simulation.py --equity "$ACCOUNT_EQUITY" 2>&1 | tee -a "$LOG" || true

  sleep "$MONITOR_INTERVAL"
done
