#!/usr/bin/env bash
# Regenerate consolidated dense pair×TF setups table (all columns, small sharp font).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
FONT="${EW_DENSE_SETUPS_FONT:-8}"

"$PY" scripts/export_dense_setups_table.py --font-size "$FONT"
cp reports/all_pair_tf_setups_dense.html output/all_pair_tf_setups_dense.html
cp reports/all_pair_tf_setups_dense.csv output/all_pair_tf_setups_dense.csv
echo "[dense-setups] HTML: $ROOT/reports/all_pair_tf_setups_dense.html"
echo "[dense-setups] CSV:  $ROOT/reports/all_pair_tf_setups_dense.csv"
