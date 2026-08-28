#!/usr/bin/env bash
# Run scripts/run_autonomous_daily.sh on a loop (default: every 24h).
set -euo pipefail
cd "$(dirname "$0")/.."

INTERVAL="${EW_AUTONOMOUS_INTERVAL:-86400}"
PID_FILE="${EW_AUTONOMOUS_PID:-output/autonomous/daemon.pid}"
mkdir -p "$(dirname "$PID_FILE")"
echo $$ >"$PID_FILE"

echo "[autonomous-daemon] pid=$$ interval=${INTERVAL}s"
while true; do
  bash scripts/run_autonomous_daily.sh || echo "[autonomous-daemon] cycle failed — retry next interval"
  sleep "$INTERVAL"
done
