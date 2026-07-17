"""Batch runner enhancements: summary export and top-N crypto execution."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from engine.batch import run_batch, save_batch_json
from engine.report import save_detailed_csv, save_detailed_markdown
from engine.outcome_report import save_outcomes_csv
from engine.full_report import export_all_reports
from engine.autodream import build_monitor_queue, save_monitor_queue
from engine.limit_orders_export import export_limit_orders
from fetchers.pairs import fetch_top_pairs, write_pairs_csv

DEFAULT_TFS = ["1w", "1d", "4h", "1h", "15m"]

_REPORTS_DIR = Path("reports")
_EXECUTABLE_FIELDS = [
  "symbol", "timeframe", "direction", "honest_execution_tier", "wae",
  "risk_budget_usd", "position_notional_usd", "leg1_usd", "leg2_usd", "leg3_usd", "leg4_usd",
  "stop_loss", "tp1", "tp2", "tp3", "dca_profile",
]


def _sync_reports_from_export(output_dir: Path, limit_meta: dict) -> None:
  """Copy key artifacts from gitignored output/ into tracked reports/."""
  import shutil

  _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
  pairs = [
    (output_dir / "COMPLETE_TRADING_ANALYSIS.md", _REPORTS_DIR / "COMPLETE_TRADING_ANALYSIS.md"),
    (output_dir / "latest_trade_setups_matrix.html", _REPORTS_DIR / "trade_setups_matrix.html"),
    (Path("reports/HISTORICAL_PERFORMANCE.md"), _REPORTS_DIR / "HISTORICAL_PERFORMANCE.md"),
  ]
  for src, dst in pairs:
    if src.exists() and src.resolve() != dst.resolve():
      shutil.copy2(src, dst)

  csv_src = Path(limit_meta.get("latest_csv", output_dir / "latest_limit_orders_all_tf.csv"))
  if csv_src.exists():
    rows = list(csv.DictReader(csv_src.open()))
    exec_rows = [r for r in rows if r.get("row_type") == "primary" and r.get("gtc_tier") == "executable"]
    dst_csv = _REPORTS_DIR / "latest_executable_pair_tf.csv"
    with dst_csv.open("w", newline="") as f:
      w = csv.DictWriter(f, fieldnames=_EXECUTABLE_FIELDS, extrasaction="ignore")
      w.writeheader()
      w.writerows(sorted(exec_rows, key=lambda x: (x["symbol"], x["timeframe"])))


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
  detailed_path = out / f"top{n}_detailed_{ts}.csv"
  outcomes_path = out / f"top{n}_outcomes_{ts}.csv"
  full_path = out / f"top{n}_full_{ts}"
  markdown_path = out / f"top{n}_report_{ts}.md"

  pairs = fetch_top_pairs(n=n, quote=quote)
  write_pairs_csv(pairs, str(pairs_csv))

  print(f"\n[batch] Running {len(pairs)} pairs × timeframes {tfs}")
  results = run_batch(str(pairs_csv), tfs, is_crypto=True)
  save_batch_json(results, str(json_path))
  save_batch_summary_csv(results, str(summary_path))
  save_detailed_csv(results, str(detailed_path))
  save_detailed_markdown(results, str(markdown_path), title=f"Top {n} Crypto EW Analysis")
  save_outcomes_csv(results, str(outcomes_path))
  full_exports = export_all_reports(results, str(full_path), title=f"Top {n} Crypto — Full Analysis")
  monitor_q = build_monitor_queue(results)
  save_monitor_queue(monitor_q, str(out / "autodream" / "monitor_queue.json"))
  limit_meta = export_limit_orders(
    results,
    output_dir=out,
    account_equity=float(os.environ["ACCOUNT_EQUITY"]) if os.environ.get("ACCOUNT_EQUITY") else None,
    usdt_d_pct=float(os.environ["USDT_D_PCT"]) if os.environ.get("USDT_D_PCT") else None,
  )
  _sync_reports_from_export(out, limit_meta)

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
    "detailed_csv": str(detailed_path),
    "outcomes_csv": str(outcomes_path),
    "full_csv": full_exports["full_csv"],
    "setups_csv": full_exports["setups_csv"],
    "setups_md": full_exports.get("setups_md"),
    "full_html": full_exports["full_html"],
    "report_md": str(markdown_path),
    "monitor_queue": str(out / "autodream" / "monitor_queue.json"),
    "limit_orders_csv": limit_meta["latest_csv"],
    "limit_orders_matrix_html": limit_meta.get("matrix_html"),
    "limit_orders_meta": str(out / "autodream" / "latest_limit_orders.json"),
    "pairs_csv": str(pairs_csv),
  }
  meta_path = out / f"top{n}_meta_{ts}.json"
  with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)

  print(f"\n[batch] DONE — {len(results)} instruments")
  print(f"  JSON:    {json_path}")
  print(f"  Summary:  {summary_path}")
  print(f"  Detailed: {detailed_path}")
  print(f"  Outcomes: {outcomes_path}")
  print(f"  FULL:     {full_exports['full_csv']}")
  print(f"  HTML:     {full_exports['full_html']}")
  print(f"  Setups:   {full_exports['setups_csv']}")
  print(f"  Complete: {full_exports.get('setups_complete_csv', 'output/latest_setups_complete.csv')}")
  print(f"  Setups HTML:{full_exports.get('setups_html', 'output/latest_setups.html')}")
  print(f"  Setups MD:{full_exports.get('setups_md', 'reports/TRADE_SETUPS.md')}")
  print(f"  Report:   {markdown_path}")
  print(f"  Monitor:  {out / 'autodream' / 'monitor_queue.json'}")
  print(f"  Limits:   {limit_meta['latest_csv']} ({limit_meta['row_count']} rows, tiers {limit_meta['tier_counts']})")
  if limit_meta.get("matrix_html"):
    print(f"  Matrix:   {limit_meta['matrix_html']}")
  print(f"  Status:  {by_status}")
  print(f"  Verdict: {by_verdict}")
  return meta
