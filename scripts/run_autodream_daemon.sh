#!/usr/bin/env bash
# Autodream daemon: monitor every 5 min, full top-50 batch every hour.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

exec python3 scripts/autodream_monitor.py \
  --daemon \
  --interval "${MONITOR_INTERVAL:-300}" \
  --batch-interval "${BATCH_INTERVAL:-3600}" \
  --batch-n "${BATCH_N:-50}" \
  --batch-now \
  "$@"
