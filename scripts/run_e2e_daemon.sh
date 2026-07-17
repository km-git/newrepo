#!/usr/bin/env bash
# Continuous E2E daemon: learn → batch → monitor → paper execute → improve
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

INTERVAL="${E2E_INTERVAL:-3600}"
BATCH_N="${EW_E2E_BATCH_N:-50}"
EXECUTE="${EW_E2E_EXECUTE:-1}"

echo "[e2e-daemon] interval=${INTERVAL}s batch_n=${BATCH_N} execute=${EXECUTE}"

while true; do
  ARGS=(--batch-n "$BATCH_N")
  if [[ "$EXECUTE" == "1" ]]; then
    ARGS+=(--execute)
  fi
  python3 scripts/e2e_trading_cycle.py "${ARGS[@]}" || echo "[e2e-daemon] cycle failed — retry next interval"
  sleep "$INTERVAL"
done
