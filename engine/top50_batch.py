"""Batch runner enhancements: summary export and top-N crypto execution."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from engine.batch import run_batch, save_batch_json
from fetchers.pairs import fetch_top_pairs, write_pairs_csv

DEFAULT_TFS = ["1w", "1d", "4h", "1h", "15m"]


def _extract_row(result: dict) -> dict:
  sym = result.get("symbol", "?")
  if result.get("status") == "incomplete":
    return {
      "symbol": sym,
      "status": "incomplete",
      "verdict": "",
      "direction": "",
      "action": "",
      "confidence": "",
      "consensus_direction": "",
      "agreement_pct": "",
      "error": result.get("error", ""),
    }
  ts = result.get("trade_setup", {})
  ex = result.get("executive_decision", {})
  cons = result.get("step6_wave_consensus", {})
  return {
    "symbol": sym,
    "status": result.get("status", ""),
    "verdict": ex.get("verdict", ""),
    "direction": ex.get("direction", ""),
    "action": ts.get("action", ""),
    "confidence": ts.get("confidence", ""),
    "consensus_direction": cons.get("consensus_direction", ""),
    "agreement_pct": cons.get("agreement_pct", ""),
    "engines_valid": cons.get("engines_valid", ""),
    "error": "",
  }


def save_batch_summary_csv(results: List[dict], out_path: str) -> None:
  rows = [_extract_row(r) for r in results]
  if not rows:
    return
  with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)


def run_top_crypto_batch(
  n: int = 50,
  tfs: List[str] | None = None,
  output_dir: str = "output",
  quote: str = "USDT",
) -> Dict[str, Any]:
  """Fetch top N pairs and run full EW pipeline on all timeframes."""
  tfs = tfs or DEFAULT_TFS
  out = Path(output_dir)
  out.mkdir(parents=True, exist_ok=True)

  ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  pairs_csv = out / f"top{n}_{quote.lower()}_{ts}.csv"
  json_path = out / f"top{n}_analysis_{ts}.json"
  summary_path = out / f"top{n}_summary_{ts}.csv"

  pairs = fetch_top_pairs(n=n, quote=quote)
  write_pairs_csv(pairs, str(pairs_csv))

  print(f"\n[batch] Running {len(pairs)} pairs × timeframes {tfs}")
  results = run_batch(str(pairs_csv), tfs, is_crypto=True)
  save_batch_json(results, str(json_path))
  save_batch_summary_csv(results, str(summary_path))

  by_status: Dict[str, int] = {}
  by_verdict: Dict[str, int] = {}
  for r in results:
    st = r.get("status", "incomplete")
    by_status[st] = by_status.get(st, 0) + 1
    v = (r.get("executive_decision") or {}).get("verdict", "N/A")
    if st != "incomplete":
      by_verdict[v] = by_verdict.get(v, 0) + 1

  meta = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "pairs_count": len(pairs),
    "timeframes": tfs,
    "pairs": pairs,
    "by_status": by_status,
    "by_verdict": by_verdict,
    "json": str(json_path),
    "summary_csv": str(summary_path),
    "pairs_csv": str(pairs_csv),
  }
  meta_path = out / f"top{n}_meta_{ts}.json"
  with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)

  print(f"\n[batch] DONE — {len(results)} instruments")
  print(f"  JSON:    {json_path}")
  print(f"  Summary: {summary_path}")
  print(f"  Status:  {by_status}")
  print(f"  Verdict: {by_verdict}")
  return meta
