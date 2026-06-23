"""Batch runner enhancements: summary export and top-N crypto execution."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from engine.batch import run_batch, save_batch_json
from engine.report import save_detailed_csv, save_detailed_markdown
from engine.outcome_report import save_outcomes_csv
from engine.full_report import export_all_reports
from engine.autodream import build_monitor_queue, save_monitor_queue
from engine.paper_trading import (
  append_paper_ledger,
  apply_honesty_adjustments,
  apply_paper_to_results,
  run_paper_batch,
  save_paper_csv,
  save_paper_metrics,
)
from engine.trade_learning import apply_learning_to_outcomes, run_loss_learning_cycle
from engine.indicator_calibration import (
  accumulation_status,
  merge_setup_metadata_into_trades,
  run_calibration_accumulation_cycle,
  run_indicator_calibration,
)
from engine.system_audit import run_system_audit, apply_audit_demotions
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
  detailed_path = out / f"top{n}_detailed_{ts}.csv"
  outcomes_path = out / f"top{n}_outcomes_{ts}.csv"
  full_path = out / f"top{n}_full_{ts}"
  markdown_path = out / f"top{n}_report_{ts}.md"

  pairs = fetch_top_pairs(n=n, quote=quote)
  write_pairs_csv(pairs, str(pairs_csv))

  print(f"\n[batch] Running {len(pairs)} pairs × timeframes {tfs}")
  print("\n[batch] Indicator recalibration from paper ledger...")
  acc = accumulation_status()
  use_clean = acc.get("ready_for_clean_reestimate", False)
  calibration = run_indicator_calibration(calibrated_only=use_clean)
  if calibration.get("available"):
    kept = len(calibration.get("kept_signals", {}))
    removed = len(calibration.get("removed_signals", {}))
    src = calibration.get("source", "all_ledger")
    gen = calibration.get("calibration_generation", 0)
    print(
      f"  Calibrated from {calibration.get('closed_trades')} closed trades "
      f"(baseline WR {calibration.get('baseline_win_rate', 0):.0%}, source={src}, gen={gen}) — "
      f"kept {kept} signals, removed {removed}"
    )
    print(
      f"  Accumulation: {acc.get('calibrated_closed', 0)}/{acc.get('target_closed')} "
      f"calibrated-era closed ({acc.get('remaining_to_target')} to clean re-estimate)"
    )
  else:
    print(f"  Calibration skipped: {calibration.get('reason', 'unknown')}")

  results = run_batch(str(pairs_csv), tfs, is_crypto=True)
  save_batch_json(results, str(json_path))
  save_batch_summary_csv(results, str(summary_path))
  save_detailed_csv(results, str(detailed_path))
  save_detailed_markdown(results, str(markdown_path), title=f"Top {n} Crypto EW Analysis")
  save_outcomes_csv(results, str(outcomes_path))
  full_exports = export_all_reports(results, str(full_path), title=f"Top {n} Crypto — Full Analysis")

  print("\n[batch] Running paper trading + historical analysis on all setups...")
  paper_report = run_paper_batch(results, fetch_missing=True)
  results = apply_paper_to_results(results, paper_report)
  for r in results:
    if r.get("status") != "incomplete" and r.get("step8_outcomes"):
      r["step8_outcomes"] = apply_honesty_adjustments(r["step8_outcomes"])

  print("\n[batch] Loss learning from failed paper trades...")
  learning = run_loss_learning_cycle()
  if learning.get("available"):
    from fetchers import fetch

    for r in results:
      if r.get("status") == "incomplete":
        continue
      try:
        data = fetch(r["symbol"], tfs, is_crypto=True)
        r["step8_outcomes"] = apply_learning_to_outcomes(
          r["step8_outcomes"], r["symbol"], data, learning
        )
      except Exception as e:
        print(f"[learning] skip {r['symbol']}: {e}")

  setup_rows = []
  from engine.outcome_report import build_outcome_row
  for r in results:
    setup_rows.extend(build_outcome_row(r))
  audit = run_system_audit(paper_report.get("trades", []), setup_rows)
  print(f"\n[audit] STATUS={audit['verdict']['status']}: {audit['verdict']['shame_note']}")
  for f in audit["verdict"].get("failures", []):
    print(f"  FAIL: {f}")
  for w in audit["verdict"].get("warnings", []):
    print(f"  WARN: {w}")
  if audit["verdict"]["status"] == "FAIL":
    for r in results:
      if r.get("status") != "incomplete" and r.get("step8_outcomes"):
        r["step8_outcomes"] = apply_audit_demotions(r["step8_outcomes"], audit)

  save_batch_json(results, str(json_path))
  enriched_trades = merge_setup_metadata_into_trades(
    paper_report.get("trades", []), results, calibration
  )
  append_paper_ledger(enriched_trades)
  acc_after = run_calibration_accumulation_cycle(
    results=results,
    trades=enriched_trades,
  )
  if acc_after.get("reestimated"):
    print(
      f"\n[calibration] Clean re-estimate applied (gen {acc_after.get('calibration', {}).get('generation')}, "
      f"source={acc_after.get('calibration', {}).get('source')})"
    )
  elif acc_after.get("remaining_to_target", 0) > 0:
    print(
      f"\n[calibration] Accumulating clean data: "
      f"{acc_after.get('calibrated_closed')}/{acc_after.get('target_closed')} "
      f"({acc_after.get('remaining_to_target')} remaining)"
    )
  paper_metrics_path = save_paper_metrics(paper_report)
  paper_csv_path = save_paper_csv(paper_report)
  save_outcomes_csv(results, str(outcomes_path))
  full_exports = export_all_reports(results, str(full_path), title=f"Top {n} Crypto — Full Analysis")

  from engine.accurate_setups import (
    extract_accurate_setups,
    extract_research_setups,
    save_accurate_setups_csv,
    save_research_setups_csv,
    summarize_accurate,
    summarize_research,
  )
  accurate_rows = extract_accurate_setups(results, min_tier="C")
  accurate_csv = out / "latest_accurate_setups.csv"
  save_accurate_setups_csv(accurate_rows, accurate_csv)
  accurate_summary = summarize_accurate(accurate_rows)
  research_rows = extract_research_setups(results)
  research_csv = out / "latest_research_setups.csv"
  save_research_setups_csv(research_rows, research_csv)
  research_summary = summarize_research(research_rows)

  from engine.executive_board import apply_board_to_results, build_executive_board, save_executive_board
  executive_board = build_executive_board(results, picks_per_tf=5, max_total=30)
  results = apply_board_to_results(results, executive_board)
  board_paths = save_executive_board(executive_board)
  save_batch_json(results, str(json_path))
  print(
    f"\n[executive] Board: {executive_board['board_picks']} picks — "
    f"{executive_board.get('by_action')} — {board_paths['csv']}"
  )

  from engine.smc_paper_cohort import run_and_persist_smc_cohort
  from engine.execution_queue import build_execution_queue, save_execution_queue

  smc_cohort = run_and_persist_smc_cohort(results, fetch_missing=True)
  print(
    f"\n[smc_cohort] {smc_cohort.get('executables_found')} executables — "
    f"papered {smc_cohort.get('papered')} (FULL={smc_cohort.get('full_count')}, "
    f"PROBE={smc_cohort.get('probe_count')})"
  )

  monitor_q = build_monitor_queue(results)
  save_monitor_queue(monitor_q, str(out / "autodream" / "monitor_queue.json"))

  exec_queue = build_execution_queue(results=results, board=executive_board, approve=True)
  exec_queue_path = save_execution_queue(exec_queue, str(out / "autodream" / "execution_queue.json"))
  print(
    f"\n[execution] Queue: {exec_queue.get('approved_count')} approved, "
    f"{exec_queue.get('rejected_count')} rejected — {exec_queue_path}"
  )

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
    "paper_metrics": paper_metrics_path,
    "paper_csv": paper_csv_path,
    "paper_setups": paper_report.get("setups_papered"),
    "paper_win_rate": paper_report.get("win_rate"),
    "loss_lessons": learning.get("lessons", []) if learning.get("available") else [],
    "losses_analyzed": learning.get("losses_analyzed", 0),
    "indicator_calibration": str(out / "autodream" / "indicator_calibration.json")
    if calibration.get("available")
    else None,
    "calibration_kept_signals": len(calibration.get("kept_signals", {}))
    if calibration.get("available")
    else 0,
    "calibration_accumulation": acc_after,
    "accurate_setups_csv": str(accurate_csv),
    "accurate_setups": accurate_summary["by_tier"],
    "research_setups_csv": str(research_csv),
    "research_setups": research_summary["by_research_tier"],
    "executive_board_csv": board_paths["csv"],
    "executive_board": executive_board.get("by_action"),
    "executive_board_picks": executive_board.get("board_picks"),
    "smc_cohort": smc_cohort.get("cohort_id"),
    "smc_cohort_path": str(out / "autodream" / "smc_paper_cohort.json"),
    "execution_queue": exec_queue_path,
    "execution_approved": exec_queue.get("approved_count"),
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
  print(f"  Paper:    {paper_csv_path} ({paper_report.get('setups_papered')} setups, "
        f"win_rate={paper_report.get('win_rate')})")
  if learning.get("available"):
    print(f"  Learning: {learning.get('losses_analyzed')} losses → {len(learning.get('lessons', []))} lessons")
    print(f"  Lessons:  {out / 'autodream' / 'loss_lessons.json'}")
  print(f"  Status:  {by_status}")
  print(f"  Verdict: {by_verdict}")
  return meta
