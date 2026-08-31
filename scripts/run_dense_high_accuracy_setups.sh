#!/usr/bin/env bash
# Re-export universe/top50 batch with executive board + SQS, then dense high-accuracy table.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

INPUT="${1:-}"
if [[ -z "$INPUT" ]]; then
  INPUT=$(ls -t output/universe_full_*.json output/top50_analysis_*.json 2>/dev/null | head -1)
fi
if [[ -z "$INPUT" || ! -f "$INPUT" ]]; then
  echo "No batch JSON found. Run universe or top50 batch first." >&2
  exit 1
fi

echo "[dense] Input: $INPUT"
python3 - <<PY
import json
import os
from pathlib import Path
from engine.executive_board import apply_board_to_results, build_executive_board, save_executive_board
from engine.limit_orders_export import export_limit_orders

inp = Path("$INPUT")
batch = json.loads(inp.read_text(encoding="utf-8"))
print(f"[dense] Symbols: {len(batch)}")

board = build_executive_board(batch, picks_per_tf=8, max_total=80)
batch = apply_board_to_results(batch, board)
save_executive_board(board)

meta = export_limit_orders(
    batch,
    output_dir=Path("output"),
    account_equity=float(os.environ.get("ACCOUNT_EQUITY", "10000")),
    board=board,
    filter_executive=False,
)
print(f"[dense] Export rows: {meta.get('row_count')}")
print(f"[dense] SQS tiers: {meta.get('sqs', {}).get('sqs_by_tier')}")
print(f"[dense] SQS CSV: {meta.get('sqs_ranked_csv')}")
PY

python3 scripts/export_dense_setups_table.py \
  --input output/latest_limit_orders_all_tf.csv \
  --csv-out reports/all_pair_tf_setups_dense.csv \
  --html-out reports/all_pair_tf_setups_dense.html \
  --title "All Pair × TF Setups — Full Dense View"

python3 scripts/export_dense_setups_table.py \
  --input output/latest_limit_orders_all_tf.csv \
  --csv-out reports/high_accuracy_setups_dense.csv \
  --html-out reports/high_accuracy_setups_dense.html \
  --high-accuracy-only \
  --title "Historically Validated Trade Setups"

python3 scripts/export_dense_setups_table.py \
  --input output/latest_limit_orders_all_tf.csv \
  --csv-out reports/trade_setup_candidates_dense.csv \
  --html-out reports/trade_setup_candidates_dense.html \
  --candidate-only \
  --title "Technically Valid Trade Setup Candidates"

echo "[dense] Done."
