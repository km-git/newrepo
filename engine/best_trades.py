"""Rank and export best executable pair×TF setups from limit-order export CSV."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _f(row: dict, key: str, default: float = 0.0) -> float:
  try:
    return float(row.get(key) or default)
  except (TypeError, ValueError):
    return default


def score_setup(row: dict) -> float:
  """Composite rank: WAE confluence, readiness, RR, tier, historical lift."""
  tier = row.get("gtc_tier", "")
  if tier != "executable":
    return -1.0
  wae = _f(row, "wae")
  readiness = _f(row, "readiness_score")
  rr = _f(row, "rr_tp2") or _f(row, "rr_tp1")
  honest = row.get("honest_execution_tier", "")
  tier_bonus = {"full": 25.0, "probe": 10.0}.get(honest, 0.0)
  return wae * 0.45 + readiness * 0.30 + rr * 10.0 + tier_bonus


def rank_executable_setups(
  rows: List[dict],
  *,
  limit: int = 100,
  min_wae: float = 0.0,
) -> List[dict]:
  ranked: List[dict] = []
  for row in rows:
    if row.get("row_type") != "primary":
      continue
    if row.get("gtc_tier") != "executable":
      continue
    if _f(row, "wae") < min_wae:
      continue
    scored = dict(row)
    scored["_rank_score"] = round(score_setup(row), 4)
    ranked.append(scored)
  ranked.sort(key=lambda r: r["_rank_score"], reverse=True)
  return ranked[:limit]


def load_limit_order_rows(csv_path: str | Path) -> List[dict]:
  path = Path(csv_path)
  if not path.exists():
    return []
  with path.open() as f:
    return list(csv.DictReader(f))


def export_best_trades(
  csv_path: str | Path = "output/latest_limit_orders_all_tf.csv",
  output_dir: str | Path = "output/v6_scanner",
  *,
  top_n: int = 100,
) -> Dict[str, Any]:
  rows = load_limit_order_rows(csv_path)
  best = rank_executable_setups(rows, limit=top_n)
  out = Path(output_dir)
  out.mkdir(parents=True, exist_ok=True)
  ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

  fields = [
    "symbol", "timeframe", "direction", "gtc_tier", "honest_execution_tier",
    "wae", "readiness_score", "rr_tp1", "rr_tp2", "stop_loss", "tp1", "tp2", "tp3",
    "position_notional_usd", "risk_budget_usd", "dca_profile", "_rank_score",
  ]
  csv_out = out / f"best_trades_{ts}.csv"
  latest = out / "best_trades_latest.csv"
  with csv_out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(best)
  if best:
    import shutil
    shutil.copy2(csv_out, latest)

  summary = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "source_csv": str(csv_path),
    "executable_scanned": sum(1 for r in rows if r.get("gtc_tier") == "executable" and r.get("row_type") == "primary"),
    "top_n": len(best),
    "best_trades_csv": str(csv_out),
    "best_trades_latest": str(latest),
    "top_10": [
      {
        "symbol": r.get("symbol"),
        "timeframe": r.get("timeframe"),
        "direction": r.get("direction"),
        "wae": r.get("wae"),
        "readiness_score": r.get("readiness_score"),
        "rr_tp2": r.get("rr_tp2"),
        "score": r.get("_rank_score"),
      }
      for r in best[:10]
    ],
  }
  json_out = out / "best_trades_latest.json"
  json_out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
  return summary
