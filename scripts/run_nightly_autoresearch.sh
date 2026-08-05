#!/usr/bin/env bash
# Nightly: top-N batch → autoresearch eval → goal-mode quick (no extra proposal spam).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
N="${EW_NIGHTLY_BATCH_N:-15}"
OUT="${EW_NIGHTLY_OUT:-output/nightly}"
mkdir -p "$OUT"

export EW_WEB_INTEL=0
export EW_WS_ENABLED=0
export EW_OKF_BRAIN_DIR="${EW_OKF_BRAIN_DIR:-/tmp/ew-okf-nightly}"
export EW_HEALTH_REQUIRE_ARTIFACTS=0
export EW_GOAL_MODE_AUTORESEARCH=0
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

echo "==> Nightly autoresearch: top-${N} crypto batch"
"$PY" ew_tool.py --top "$N" --crypto

LATEST="$(ls -t output/top*_analysis_*.json 2>/dev/null | head -1 || true)"
if [ -z "$LATEST" ]; then
  echo "ERROR: no analysis JSON in output/" >&2
  exit 1
fi
cp "$LATEST" "$OUT/latest_analysis.json"
echo "$LATEST" > "$OUT/analysis_source_path.txt"

echo "==> AutoResearch eval on $LATEST"
"$PY" - <<PY
import json
from pathlib import Path
from engine.autoresearch import run_autoresearch_eval_loop

out = Path("${OUT}")
latest = out / "analysis_source_path.txt"
analysis_path = latest.read_text(encoding="utf-8").strip()
result = run_autoresearch_eval_loop(analysis_path=analysis_path)
(out / "autoresearch_eval.json").write_text(
  json.dumps(result, indent=2, default=str), encoding="utf-8"
)
print(json.dumps(result.get("best") or {}, indent=2))
PY

echo "==> Goal-mode quick (learn + record + validate)"
"$PY" - <<PY
import json
from pathlib import Path
from engine.goal_mode import run_goal_mode_cycle

out = Path("${OUT}")
result = run_goal_mode_cycle(
  batch_n=0,
  execute_paper=False,
  skip_batch=True,
  skip_monitor=True,
)
(out / "goal_mode_full.json").write_text(
  json.dumps(result, indent=2, default=str), encoding="utf-8"
)
print("goal_ok=", result.get("ok"), "fitness=", (result.get("phases") or {}).get("backtest", {}).get("fitness"))
PY

"$PY" - <<PY
import json
from pathlib import Path

out = Path("${OUT}")
eval_data = json.loads((out / "autoresearch_eval.json").read_text(encoding="utf-8"))
goal = json.loads((out / "goal_mode_full.json").read_text(encoding="utf-8"))
summary = {
  "batch_n": int("${N}"),
  "analysis_source": (out / "analysis_source_path.txt").read_text(encoding="utf-8").strip(),
  "autoresearch_best": eval_data.get("best"),
  "evaluated_count": len(eval_data.get("evaluated") or []),
  "goal_ok": goal.get("ok"),
  "goal_healthy": goal.get("healthy"),
  "backtest_fitness": (goal.get("phases") or {}).get("backtest", {}).get("fitness"),
  "report_path": goal.get("report_path"),
}
(out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
PY

if [ -f output/autoresearch/experiments.jsonl ]; then
  cp output/autoresearch/experiments.jsonl "$OUT/experiments.jsonl"
fi
if [ -f output/goal_mode/last_run.json ]; then
  cp output/goal_mode/last_run.json "$OUT/goal_mode_last_run.json"
fi
if [ -f output/latest_limit_orders_all_tf.csv ]; then
  cp output/latest_limit_orders_all_tf.csv "$OUT/latest_limit_orders_all_tf.csv"
fi

echo "==> Done. Artifacts under $OUT"
