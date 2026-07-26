#!/usr/bin/env bash
# Continuous AutoResearch daemon: top-N batch → eval → goal-mode quick, on a loop.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

INTERVAL="${EW_AUTORESEARCH_INTERVAL:-3600}"
BATCH_N="${EW_NIGHTLY_BATCH_N:-15}"
LOG_DIR="${EW_AUTORESEARCH_DAEMON_LOG_DIR:-output/nightly/daemon}"
PID_FILE="${EW_AUTORESEARCH_DAEMON_PID:-output/nightly/daemon.pid}"

mkdir -p "$LOG_DIR"
echo $$ > "$PID_FILE"

export EW_WEB_INTEL=0
export EW_WS_ENABLED=0
export EW_OKF_BRAIN_DIR="${EW_OKF_BRAIN_DIR:-/tmp/ew-okf-autoresearch-daemon}"
export EW_HEALTH_REQUIRE_ARTIFACTS=0
export EW_GOAL_MODE_AUTORESEARCH=0
export EW_NIGHTLY_BATCH_N="$BATCH_N"
export EW_NIGHTLY_OUT="${EW_NIGHTLY_OUT:-output/nightly}"

echo "[autoresearch-daemon] pid=$$ interval=${INTERVAL}s batch_n=${BATCH_N} log_dir=${LOG_DIR}"
echo "[autoresearch-daemon] started $(date -u +%Y-%m-%dT%H:%M:%SZ)"

cycle=0
while true; do
  cycle=$((cycle + 1))
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  log="${LOG_DIR}/cycle_${cycle}_${stamp}.log"
  echo "[autoresearch-daemon] cycle=${cycle} log=${log}"
  if bash scripts/run_nightly_autoresearch.sh >"$log" 2>&1; then
    echo "[autoresearch-daemon] cycle=${cycle} ok"
  else
    echo "[autoresearch-daemon] cycle=${cycle} failed (see ${log})"
  fi
  echo "[autoresearch-daemon] sleeping ${INTERVAL}s"
  sleep "$INTERVAL"
done
