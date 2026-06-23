#!/usr/bin/env bash
# Install cron entries for the live trading loop.
# Usage: ./scripts/install_live_cron.sh [--dry-run] [--user $USER]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
DRY_RUN_FLAG=""
USER_NAME="${USER:-$(whoami)}"
TICK_INTERVAL="${TICK_INTERVAL:-300}"
BATCH_INTERVAL="${BATCH_INTERVAL:-3600}"
LOG_DIR="${LOG_DIR:-$ROOT/output/autodream/logs}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN_FLAG="--dry-run" ;;
    --user) USER_NAME="$2"; shift ;;
    --tick-interval) TICK_INTERVAL="$2"; shift ;;
    --batch-interval) BATCH_INTERVAL="$2"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

mkdir -p "$LOG_DIR"

CRON_LINE="*/5 * * * * cd $ROOT && PYTHONPATH=$ROOT $PYTHON scripts/run_live_loop.py --tick-only $DRY_RUN_FLAG --max-executions 3 >> $LOG_DIR/live_tick.log 2>&1"
HOURLY_LINE="0 * * * * cd $ROOT && PYTHONPATH=$ROOT $PYTHON scripts/run_live_loop.py --force-batch --max-executions 5 $DRY_RUN_FLAG >> $LOG_DIR/live_batch.log 2>&1"

echo "Proposed crontab entries for user $USER_NAME:"
echo ""
echo "# Live loop — monitor + execute every 5 min"
echo "$CRON_LINE"
echo ""
echo "# Hourly top-50 batch refresh + execution queue rebuild"
echo "$HOURLY_LINE"
echo ""
echo "Log directory: $LOG_DIR"
echo ""
read -r -p "Install these cron entries? [y/N] " confirm
if [[ "${confirm,,}" != "y" ]]; then
  echo "Aborted."
  exit 0
fi

( crontab -u "$USER_NAME" -l 2>/dev/null | grep -v "run_live_loop.py" || true
  echo "$CRON_LINE"
  echo "$HOURLY_LINE"
) | crontab -u "$USER_NAME" -

echo "Cron installed. Verify with: crontab -u $USER_NAME -l"
