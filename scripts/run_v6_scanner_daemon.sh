#!/usr/bin/env bash
# V6 continuous scanner: 1000-pair universe (spot+swap), 6 TFs, best-trade ranking 24/7.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

# V6 setup: 15m, 1h, 4h, 12h, 1d, 1w
export EW_V6_SETUP="${EW_V6_SETUP:-1}"
export EW_SCANNER_PAIRS="${EW_SCANNER_PAIRS:-1000}"
export EW_SCANNER_CHUNK="${EW_SCANNER_CHUNK:-50}"
export EW_SCANNER_INCLUDE_SWAP="${EW_SCANNER_INCLUDE_SWAP:-1}"
export ACCOUNT_EQUITY="${ACCOUNT_EQUITY:-50000}"
export USDT_D_PCT="${USDT_D_PCT:-8.2}"
export EW_PAPER_AFTER_BATCH="${EW_PAPER_AFTER_BATCH:-0}"
export EW_WEB_INTEL="${EW_WEB_INTEL:-0}"
export EW_WS_ENABLED="${EW_WS_ENABLED:-0}"

CHUNK_INTERVAL="${EW_V6_CHUNK_INTERVAL:-1800}"   # 30 min between chunk scans
FULL_INTERVAL="${EW_V6_FULL_INTERVAL:-21600}"    # 6h between full-universe refreshes
MONITOR_INTERVAL="${EW_V6_MONITOR_INTERVAL:-300}"
LOG_DIR="${EW_V6_LOG_DIR:-output/v6_scanner}"
PID_FILE="${EW_V6_PID_FILE:-output/v6_scanner/daemon.pid}"
mkdir -p "$LOG_DIR"
echo $$ >"$PID_FILE"

STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/daemon_${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1

echo "[v6-daemon] started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[v6-daemon] pairs=${EW_SCANNER_PAIRS} chunk=${EW_SCANNER_CHUNK} tfs=V6 chunk_iv=${CHUNK_INTERVAL}s full_iv=${FULL_INTERVAL}s"

LAST_FULL=0
while true; do
  NOW=$(date +%s)

  if (( NOW - LAST_FULL >= FULL_INTERVAL )); then
    echo "=== V6 FULL UNIVERSE SCAN $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    "$PY" -c "
import json
from engine.v6_scanner import run_v6_full_batch
r = run_v6_full_batch()
print(json.dumps({'universe': r.get('universe_size'), 'top10': (r.get('best_trades') or {}).get('top_10')}, indent=2))
" || echo "[v6-daemon] full scan failed — continuing"
    LAST_FULL=$NOW
  else
    echo "=== V6 CHUNK SCAN $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    "$PY" -c "
import json
from engine.v6_scanner import run_v6_chunk_scan
r = run_v6_chunk_scan(include_swap=${EW_SCANNER_INCLUDE_SWAP})
print(json.dumps({
  'chunk': r.get('chunk_pairs'),
  'universe': r.get('universe_size'),
  'offset_next': r.get('chunk_offset_next'),
  'top10': (r.get('best_trades') or {}).get('top_10'),
}, indent=2))
" || echo "[v6-daemon] chunk scan failed — continuing"
  fi

  echo "=== MONITOR QUEUE $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "$PY" scripts/autodream_monitor.py --once --monitor-only --batch-interval 0 2>&1 || true

  if [[ "${EW_V6_AUTORESEARCH:-1}" == "1" ]]; then
    echo "=== AUTORESEARCH EVAL $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    EW_NIGHTLY_SKIP_BATCH=1 bash scripts/run_nightly_autoresearch.sh 2>&1 || true
  fi

  echo "[v6-daemon] sleep ${CHUNK_INTERVAL}s"
  sleep "$CHUNK_INTERVAL"
done
